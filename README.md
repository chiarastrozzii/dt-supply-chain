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
