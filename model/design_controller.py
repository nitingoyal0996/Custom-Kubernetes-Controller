import math
import argparse

def design_pi_controller(settling_time, max_overshoot, a, b):
    """
    Calculate r (pole radius)
    - r = e^(-4/settling_time)
    
    Calculate theta (pole angle)
    - θ = π * (log(r) / log(max_overshoot))
    
    Detailed PI Controller Design using Pole Placement
    
    Algebraic Derivation Steps:
    1. Characteristic Equation: z² + (-a-1+KI*b)z + (a + KP*b) = 0
    2. Desired Characteristic Polynomial: z² - 2r*cos(θ)z + r²
    
    Coefficient Matching:
    - z coefficient: -a-1+KI*b = -2r*cos(θ)
    - Rearranging: KI*b = -2r*cos(θ) + a + 1
    - Ki = [-2r*cos(θ) + a + 1] / b
    
    - Constant term: a + KP*b = r²
    - Rearranging: KP*b = r² - a
    - Kp = [r² - a] / b
    """
    
    r = math.exp(-4 / settling_time)
    theta = math.pi * (math.log(r) / math.log(max_overshoot/100))

    # b: System gain, a: System pole
    
    # Ki Calculation
    # Derive from z coefficient matching
    # KI*b = -2r*cos(θ) + a + 1
    # Ki = [-2r*cos(θ) + a + 1] / b
    Ki = (-2 * r * math.cos(theta) + a + 1) / b
    
    # Kp Calculation
    # Derive from constant term matching
    # a + KP*b = r²
    # KP*b = r² - a
    # Kp = [r² - a] / b
    Kp = (r**2 - a) / b
    
    return Kp, Ki


def main():
    args = argparse.ArgumentParser("Submit controller parameters - a, b, settling time, max overshoot")

    args.add_argument("--a", type=float, default=1, help="System pole")
    args.add_argument("--b", type=float, default=0.25, help="System gain")
    args.add_argument("--settling-time", type=float, default=2, help="Settling time in seconds")
    args.add_argument("--max-overshoot", type=float, default=5, help="Max overshoot in %")
    args = args.parse_args()

    Kp, Ki = design_pi_controller(args.settling_time, args.max_overshoot, args.a, args.b)

    print(f"Kp,{Kp:.4f}")
    print(f"Ki,{Ki:.4f}")

if __name__ == "__main__":
    # python ./design_controller.py --a 0.8709 --b -0.6688 --settling-time 2 --max-overshoot 5 > ./data/control.csv
    main()