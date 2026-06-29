# Multi-Agent Digital Twin
This repository contains an end-to-end **Digital Twin (DT) framework** for simulating, forecasting, and optimizing supply chain operations. The project bridges a simulation layer with an AI-driven predictive/prescriptive analytics engine, accessible through a descriptive module.

---

## Repository Architecture

The repository is organized as follows:

*   **`actual_system.alp`** & **`3d/`**: The core AnyLogic simulation model representing the operational layer of the digital twin.
*   **`Libraries/`**: Project dependencies, including the configuration files required to bridge AnyLogic with Python (`pypeline.properties`).
*   **`prescriptive/`**: Modules dedicated to prescriptive analytics, optimization scripts, and decision-support logic.
*   **`forecast_engine.py`**: The time-series forecasting pipeline using Prophet model to estimate upcoming order volumes.
*   **`brain.py`**: The asynchronous bridge which uses background threads to capture real-time data from the simulation and stream them to the web dashboard server.
*   **`app.py`**: Front-end web application for the digital twin, responsible for rendering the descriptive layer (real-time data and visualizations) and interfacing with the predictive and prescriptive components.
*   **`config.json`**: Configurable parameters for simulation setup.

---

## Requirements
Before running the project, ensure that the following software is installed:

- **AnyLogic** 8.9.8 or later
- **Python** 3.10 or later

## Installation

### 1. Clone the repository

```bash
git clone <>
cd <dt-supply-chain>
```

### 2. Create a Python virtual environment

It is recommended to use a dedicated virtual environment.

**Windows**

```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/macOS**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install the required Python packages
Install all project dependencies using:

```bash
pip install -r requirements.txt
```

---

## AnyLogic Configuration

Before running the simulation, complete the following configuration steps.

### 1. Open the AnyLogic Model

Open the project using **AnyLogic 8.9.8** (or a later version).

### 2. Configure the Pypeline Connection

The project uses the **PyCommunicator** block to establish communication between AnyLogic and Python.

1. Start the simulation.
2. While the simulation is running, select the **PyCommunicator** block in the **Main** agent.
3. In the inspection panel, verify that:
   - the connection has been successfully established;
   - the correct Python interpreter is being used (preferably the one from the project's virtual environment);
   - no error messages are displayed.

If the connection cannot be established, ensure that:
- Python is installed and available in your system `PATH`;
- the virtual environment is activated;
- all dependencies have been installed using:

```bash
pip install -r requirements.txt
```

### 3. Configure the Project

Open `config.json` and adjust the project settings according to your environment, including:

- input and output directories
- simulation parameters

---
## Running the Digital Twin

The application is designed to be used in three sequential phases: **descriptive**, **predictive**, and **prescriptive**.

### 1. Launch the Web Application

Inside your virtual machine start the Streamlit dashboard:

```bash
streamlit run app.py
```

---

### 2. Run the Simulation (Descriptive Module)

Open the AnyLogic model and start the simulation.

While the simulation is running, the **Descriptive** module of the dashboard displays the real-time state of the supply chain, including:

- key performance indicators (KPIs);
- interactive graphical visualizations.

To obtain meaningful forecasting results, it is recommended to simulate **at least two years** of operation. However, a minimum simulation horizon of **30 simulated days** is required to generate an initial forecast.

Once the desired simulation horizon has been reached, stop the simulation.

---

### 3. Generate Demand Forecasts (Predictive Module)

The forecasting model can be executed in one of two ways:

- by clicking **Generate 1-Year Demand Forecast** from the left navigation bar on the dashboard
- manually by running within the virtual machine

```bash
python forecast_engine.py
```

> **Note**
> Running `forecast_engine.py` generates the forecast data required by the prescriptive module. Therefore, this step must be completed before using the optimization assistant.

After the forecast has been generated, the **Predictive** module on the dashboard displays:

- the forecasted demand for the following simulated year
- prediction confidence intervals;
- forecasting performance metrics, including:
  - Root Mean Square Error (RMSE);
  - Mean Absolute Error (MAE).

---

### 4. Use the Prescriptive Module

Select **Open AI Assistant Chat** from the left navigation panel.

The dashboard provides an AI-powered assistant that can answer questions about the supply chain and recommend operational decisions based on the available data.

You can either:

- select one of the predefined prompt
- type your own question into the chat interface

The assistant combines information from:

- the descriptive module;
- the demand forecast generated by the predictive module;
- optimization routines;
- specialized analysis tools.

> **Important**
> The forecasting engine must have been executed successfully before using the prescriptive module, as it relies on the forecast CSV files generated by `forecast_engine.py`.
