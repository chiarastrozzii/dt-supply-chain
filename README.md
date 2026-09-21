# Multi-Agent Digital Twin

<p align="left">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+"></a>
  <a href="https://www.anylogic.com/"><img src="https://img.shields.io/badge/AnyLogic-8.9.8%2B-blue" alt="AnyLogic 8.9.8+"></a>
  <a href="https://streamlit.io/"><img src="https://img.shields.io/badge/Dashboard-Streamlit-FF4B4B?logo=streamlit&logoColor=white" alt="Streamlit"></a>
  <a href="https://facebook.github.io/prophet/"><img src="https://img.shields.io/badge/Forecasting-Prophet-008080" alt="Prophet"></a>
</p>

This repository provides an end-to-end Digital Twin (DT) framework for simulating, forecasting, and optimizing complex systems. Designed as an extensible pipeline, it allows you to plug in your own AnyLogic simulation model (`.alp`) and adapt the analytics engines to your domain.

A complete **Supply Chain model** is included as a reference implementation to demonstrate the framework's descriptive, predictive, and prescriptive capabilities through a unified web interface.

## Dashboard
### Descriptive Module

<p align="center">
  <img src="images/descriptive.png" width="500"><br>
</p>

### Predictive Module

<p align="center">
  <img src="images/predictive_graph.png" width="48%">
  <img src="images/predictive_metrics.png" width="48%">
</p>

### Prescriptive Module

<p align="center">
  <img src="images/prescriptive.png" width="500"><br>
</p>

---

## Repository Architecture

The repository is organized as follows:

*   **`actual_system.alp`** & **`3d/`**: The core AnyLogic simulation model (default: supply chain reference model).
*   **`Libraries/`**: Project dependencies, including the configuration files required to bridge AnyLogic with Python (`pypeline.properties`).
*   **`prescriptive/`**: Modules dedicated to prescriptive analytics, optimization scripts, and decision-support logic.
*   **`forecast_engine.py`**: Time-series forecasting engine (Prophet based), used to estimate future customer order volumes.
*   **`brain.py`**: Asynchronous communication layer responsible for collecting real-time simulation data and streaming them to the web dashboard.
*   **`app.py`**: Streamlit-based web application providing the user interface for the descriptive, predictive, and prescriptive modules.
*   **`config.json`**: Configurable parameters for simulation setup.

---

## Requirements
Before running the project, ensure that the following software is installed:

- **AnyLogic** 8.9.8 or later
- **Python** 3.10 or later
- **GitHub Personal Access Token (PAT)**: Required to authenticate the LLM API utilized by the Prescriptive Module's AI Assistant.

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/chiarastrozzii/dt-supply-chain.git
cd dt-supply-chain
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
## Workflow

The overall workflow is summarized below:
1. Export your GitHub token and launch the Streamlit dashboard.
2. Run your AnyLogic simulation.
3. Monitor real-time KPIs through the descriptive module.
4. Generate system forecasts (via UI or local engine).
5. Use the AI assistant to analyze forecasts and generate prescriptive recommendations.
---

## AnyLogic Configuration

Before running the simulation, complete the following configuration steps.

### 1. Open the AnyLogic Model

Open the AnyLogic project(`.alp`).

### 2. Configure the Pypeline Connection

The framework uses the **PyCommunicator** block to establish communication between AnyLogic and Python.

1. Start the simulation.
2. While running, select the **PyCommunicator** block in the **Main** agent.
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

To use the Prescriptive Module, you need to export your `GITHUB_TOKEN` as an environment variable before launching the Streamlit app. This token is required to authenticate the AI Assistant's API calls.

Within your activated virtual environment, export the token and start the dashboard using the commands corresponding to your operating system:

**Linux/macOS**
```bash
export GITHUB_TOKEN="your_github_token_here"
streamlit run app.py
```

**Windows (Command Prompt)**
```bash
set GITHUB_TOKEN=your_github_token_here
streamlit run app.py
```

**Windows (PowerShell)**
```bash
$env:GITHUB_TOKEN="your_github_token_here"
streamlit run app.py
```
---

### 2. Run the Simulation (Descriptive Module)

Open the AnyLogic model and start the simulation.

While the simulation is running, the **Descriptive** module, through the dashboard, displays real-time metrics and KPIs generated by the simulation.

> **Note:** To obtain meaningful forecasting results, it is recommended to simulate **at least two years** of operation. However, a minimum simulation horizon of **30 simulated days** is required to generate an initial forecast.

Once the desired simulation horizon has been reached, stop the simulation before generating the demand forecast.

---

### 3. Generate the Demand Forecast (Predictive Module)

The forecasting model can be executed in one of two ways:

- **via Dashboard:**  Clicking **Generate 1-Year Demand Forecast** from the left navigation bar on the dashboard
- **Locally via Terminal:** from the activated virtual environment by running the forecasting engine:

```bash
python forecast_engine.py
```

> **Note**
> Running `forecast_engine.py` generates the forecast data required by the prescriptive module. Therefore, this step must be completed before using the optimization assistant.

After the forecast has been generated, the **Predictive** module on the dashboard displays performance metrics, prediction intervals, and error metrics (RMSE/MAE).

---

### 4. Use the Prescriptive Module

Select the **Prescriptive** module from the left navigation panel.

The dashboard provides an AI-powered assistant that leverages real-time simulation data, historical forecasts, and optimization logic to recommend actionable decisions for your system.

You can either:

- select one of the predefined prompts
- type your own question into the chat interface

The assistant uses information from:

- the descriptive module;
- the demand forecast generated by the predictive module;
- optimization routines;
- specialized analysis tools.

> **Important**
> The forecasting engine must have been executed successfully before using the prescriptive module, as it relies on the forecast CSV files generated by `forecast_engine.py`. Additionally, the backend AI features will fail if the `GITHUB_TOKEN` environment variable was not successfully exported in Step 1.

---

## Authors
Chiara Strozzi \
Stefano Genetti \
Giovanni Iacca
