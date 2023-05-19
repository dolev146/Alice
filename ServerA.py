from flask import Flask, request, jsonify
import requests
import time
import random
from sympy import is_quad_residue

app = Flask(__name__)

alice_ready = False


# tools
def xgcd(a, b):
    """Euclid's extended algorithm:
    Given a, b, find gcd, x, y that solve the equation:
    ax + by = gcd(a, b)
    """
    x, y = 0, 1
    u, v = 1, 0
    gcd = b
    while a != 0:
        q, r = divmod(gcd, a)
        m, n = x - u * q, y - v * q
        gcd, a, x, y, u, v = a, r, u, v, m, n
    return gcd, x, y


def divide(A, B, m):
    """Modular division:
    Returns integer z such that: z * B mod m == A.
    If there is more than one (i.e. when gcd(B, m) > 1) - returns the smallest such integer.
    """
    assert 0 <= A < m, "Invalid A value"
    assert 0 <= B < m, "Invalid B value"

    gcd, x, y = xgcd(B, m)
    if A % gcd == 0:
        q = A // gcd
        return ((x + m) * q) % (m // gcd)
    else:
        raise ValueError("no quotient")


def multiply_modulo_big(num1, num2, m):
    num1 %= m
    result = 0
    while num2 > 0:
        if num2 % 2 == 1:
            result = (result + num1) % m
        num1 = (num1 * 2) % m
        num2 //= 2
    return result


# is_prime function
def is_prime(n):
    if n <= 1:
        return False
    elif n <= 3:
        return True
    else:
        for i in range(2, int(n**0.5) + 1):
            if n % i == 0:
                return False
    return True


class Participant:
    def __init__(self, bit):
        self.bit = bit


class Alice(Participant):
    def __init__(self, bit, q):
        super().__init__(bit)
        self.q = q
        self.k = random.randint(0, q - 1)
        self.p = 2 * self.q + 1
        self.g = self.fing_g()

        # print(f"k={self.k} g={self.g}")

    def send(self):
        r = random.randint(2, self.q - 1)
        print(f"r={r}")
        if self.bit == 0:
            cA = (pow(self.g, r, self.p), pow(self.g, r * self.k, self.p))
            print(f"cA={cA}")
        else:
            cA = (
                pow(self.g, r, self.p),
                (self.g * pow(self.g, r * self.k, self.p)) % self.p,
            )
            print(f"cA={cA}")
        return cA, self.q, self.g, pow(self.g, self.k, self.p)

    def secureResult(self, cB):
        return divide(cB[1], pow(cB[0], self.k, self.p), self.p)

    def fing_g(self):
        while True:
            candidate = random.randint(2, self.p - 2)
            if is_quad_residue(candidate, self.p):
                return candidate


@app.route("/health_random", methods=["GET"])
def health():
    i = 0
    while not alice_ready:
        time.sleep(0.1)
        i += 1
        if i % 20 == 0:
            print("Alice is waiting for Bob")
            print(f"alice_ready={alice_ready}")
    return jsonify({"status": "ok"}), 200


@app.route("/AliceBit", methods=["POST"])
def AliceBit():
    global Alice_instance
    global alice_ready
    alice_ready = False
    private_data = request.get_json()
    if private_data is None:
        return jsonify({"error": "No data provided"}), 400
    if "bA" not in private_data:
        return jsonify({"error": "No bit provided"}), 400
    if int(private_data["bA"]) not in [0, 1]:
        return jsonify({"error": "Invalid bit provided"}), 400
    q = 23
    Alice_instance = Alice(int(private_data["bA"]), q)
    alice_ready = True
    # wait for Bob to health check localhost:5001/health
    print("Alice is ready")
    bob_health = requests.get("https://bob-ir8f.onrender.com/health")
    print(bob_health.status_code)
    if bob_health.status_code != 200:
        return jsonify({"error": "Bob is not ready"}), 400
    else:
        return jsonify(start()), 200


@app.route("/start", methods=["POST"])
def start():
    private_data = request.get_json()
    # do some calculations
    public_data = {}
    (
        public_data["cA"],
        public_data["q"],
        public_data["g"],
        public_data["gk"],
    ) = Alice_instance.send()
    # send to server B and wait for a response
    print(f"public_data={public_data}")
    response = requests.post("https://bob-ir8f.onrender.com/calculate", json=public_data)
    rst_from_bob = response.json()
    decrypted_result = Alice_instance.secureResult(rst_from_bob["cB"])
    print(f"decrypted_result={decrypted_result}")
    if decrypted_result == 1:
        data = {"result": "0"}
    else:
        data = {"result": "1"}

    # send back to server B and third party
    requests.post("https://bob-ir8f.onrender.com/end", json=data)
    return data


@app.route("/", methods=["GET"])
def index():
    return "Hello, Alice!"

if __name__ == "__main__":
    alice_ready = False
    app.run()





