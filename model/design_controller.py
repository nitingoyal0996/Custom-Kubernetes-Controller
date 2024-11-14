import math
import argparse

def design_pi_controller(settling_time, max_overshoot, system_params):
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
    b = system_params.get('b', 1)
    a = system_params.get('a', 0.5)
    
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
    # defaults
    system_params = {
        'b': 10.43,     # Adjustable system gain
        'a': -0.001     # Adjustable system pole
    }

    args = argparse.ArgumentParser("Submit controller parameters - a, b, settling time, max overshoot")

    args.add_argument("--a", type=float, default=system_params['a'], help="System pole")
    args.add_argument("--b", type=float, default=system_params['b'], help="System gain")
    args.add_argument("--settling_time", type=float, default=2, help="Settling time in seconds")
    args.add_argument("--max_overshoot", type=float, default=5, help="Max overshoot in %")

    Kp, Ki = design_pi_controller(args.settling_time, args.max_overshoot, args.a, args.b)

    print("System Parameters:")
    print(f"System Gain (a): {args.a}")
    print(f"System Pole (b): {args.b}")

    print("PI Controller Design Results:")
    print(f"Settling Time: {args.settling_time}")
    print(f"Max Overshoot: {args.max_overshoot}%")
    print(f"Kp = {Kp:.4f}")
    print(f"Ki = {Ki:.4f}")

if __name__ == "__main__":
    main()