import pandas as pd
from matplotlib import pyplot as plt 
import numpy as np
import argparse

def load_data_from_csv(file_path):
    data = pd.read_csv(file_path)
    # "CPU Workers" (input u) and "CPU Utilization" (output y)
    u_raw = data['Max Pods'].values
    y_raw = data['CPU Utilization'].values

    return u_raw, y_raw

# Text book calculations
def normalize_data(u_raw, y_raw, u_operating_point=8, y_operating_point=80):
    u_normalized = u_raw - u_operating_point
    y_normalized = y_raw - y_operating_point
    
    return u_normalized, y_normalized

def compute_sums(u, y):
    N = len(u) - 1
    S1 = np.sum(y[:N] ** 2)
    S2 = np.sum(u[:N] * y[:N])
    S3 = np.sum(u[:N] ** 2)
    S4 = np.sum(y[:N] * y[1:])
    S5 = np.sum(u[:N] * y[1:])

    return S1, S2, S3, S4, S5

def least_squares_coefficients(S1, S2, S3, S4, S5):
    denominator = S1 * S3 - S2 ** 2
    if denominator == 0:
        raise ValueError("The denominator is zero, check your data.")
    
    a = ((S3 * S4) - (S2 * S5)) / denominator
    b = ((S1 * S5) - (S2 * S4)) / denominator
    
    return a, b

# y_hat(k+1) = a * y(k) + b * u(k)
def predict_next_output(a, b, u, y):
    y_hat = a * y + b * u
    return y_hat

def calculate_r2(y_true, y_pred):
    residuals = y_true - y_pred
    var_residuals = np.var(residuals)
    var_y = np.var(y_true)
    r2 = 1 - (var_residuals / var_y)    
    
    return r2

#### plots
def plot_utilization(x_data, y_data, filename):
    plt.figure(figsize=(6, 4))
    plt.scatter(x_data, y_data, marker='o')
    plt.title('# Pods vs CPU Utilization')
    plt.xlabel('# Pods')
    plt.ylabel('CPU Utilization')
    plt.grid()
    plt.tight_layout()
    plt.savefig(f"./data/{filename}_utilization.png")
    plt.close()
    
def plot_predictions(y_true, y_pred, filename):
    plt.figure(figsize=(10, 6))
    plt.scatter(y_true, y_pred, marker='*')
    
    # Calculate and plot the regression line
    m, b = np.polyfit(y_true, y_pred, 1)
    regression_line = m * y_true + b
    plt.plot(y_true, regression_line, color='red')

    plt.title('CPU Utilization Actual vs CPU Utilization Predicted')
    plt.xlabel('Actual')
    plt.ylabel('Predicted')
    plt.grid()
    plt.legend()
    plt.savefig(f"./data/{filename}_predictions.png")
    plt.close()


def main():
    parser = argparse.ArgumentParser(description='Analyse results for Node or Cluster')
    parser.add_argument('--filename', default='Node_data_node_1_11_14', help='Type of system to stressed')
    args = parser.parse_args()
    csv_file_path = f'./data/{args.filename}.csv'

    # Analyze system
    u_raw, y_raw = load_data_from_csv(csv_file_path)
    u_operating_point =  8 # np.average(u_raw[:-1])
    y_operating_point = 80 # np.average(y_raw[1:]) 
    print('Operating points:', u_operating_point, y_operating_point)
    u_normalized, y_normalized = normalize_data(u_raw, y_raw, u_operating_point, y_operating_point)

    S1, S2, S3, S4, S5 = compute_sums(u_normalized, y_normalized)
    a, b = least_squares_coefficients(S1, S2, S3, S4, S5)
    print(f"a,{a}")
    print(f"b,{b}")

    y_pred = predict_next_output(a, b, u_normalized[:-1], y_normalized[:-1])

    r2_score = calculate_r2(y_normalized[1:], y_pred)
    print(f"R2,{r2_score}")

    plot_predictions(y_raw[1:], y_pred+y_operating_point, args.filename)
    plot_utilization(u_raw[1:], y_pred+y_operating_point, args.filename)

if __name__ == '__main__':
    args = argparse.ArgumentParser(description='Analyse results for Node or Cluster')
    args.add_argument('--filename', help='Type of system to stressed')
    # python ./model_system.py --filename 'Node_data_node_1_11_14' > ./data/model.csv
    # cat ./data/model.csv
    main()