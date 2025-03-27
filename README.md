#Hackathon Judge AI Assitant Setup Guide

## Overview
This guide will help testers and users set up the project directory and install the required dependencies step by step.

## 1. Directory Structure
Ensure your project directory is set up as follows:
```
your_project/
├── app1.py
├── templates/
│   ├── index.html
├── uploads/
├── image.png
├── requirements.txt
├── config.ini
```
### Explanation:
- **app1.py**: Main Python script for the project.
- **templates/**: Folder to store HTML files (e.g., `index.html`).
- **uploads/**: Directory for uploaded files.
- **requirements.txt**: File containing the required dependencies.
- **config.ini**: Configuration file storing API keys.

## 2. Installation Steps

### Step 1: Clone the Repository
If using Git, open your terminal or command prompt and run:
```
git clone <repository_url>
cd your_project
```

### Step 2: Set Up a Virtual Environment (Recommended)
It is recommended to create a virtual environment to manage dependencies.
#### On Windows:
```
python -m venv venv
venv\Scripts\activate
```
#### On macOS/Linux:
```
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies
Run the following command to install all required dependencies:
```
pip install -r requirements.txt
```

### Step 4: Configure API Keys
The project requires API keys to interact with various services. Open the `config.ini` file and add your API keys in the following format:
```
[API_KEYS]
azure_subscription_key= YOUR_AZURE_SUBSCRIPTION_KEY
azure_region= YOUR_AZURE_REGION
azure_speech_endpoint= https://YOUR_AZURE_REGION_HERE.cognitiveservices.azure.com

gemini_api_key= YOUR_GEMINI_API_KEY
azure_computer_vision_key= YOUR_AZURE_COMPUTER_VISION_KEY
azure_computer_vision_endpoint= https://YOUR_AZURE_REGION_HERE.cognitiveservices.azure.com
```
#### How to Get Your API Keys
1. **Azure Subscription Key & Region:**
   - Go to [Azure Portal](https://portal.azure.com/)
   - Search for **Cognitive Services** and create a new resource.
   - After creating, go to the **Keys and Endpoint** section.
   - Copy the **Key 1** and **Region**, then paste them into `config.ini`.

2. **Azure Speech Endpoint:**
   - Follow the same steps as above but choose **Speech Services**.
   - Copy the provided **Endpoint** and update `config.ini`.

3. **Gemini API Key:**
   - Visit [Google AI Platform](https://ai.google.dev/)
   - Sign up and generate an API key.
   - Copy and paste it into `config.ini`.

4. **Azure Computer Vision API:**
   - In Azure Portal, create a **Computer Vision** resource.
   - Find your **Key 1** and **Endpoint** in the resource settings.
   - Update `config.ini` accordingly.

### Step 5: Run the Project
To start the project, execute:
```
python app1.py
```

### Step 6: Open the Application
If the script runs a web application, open your browser and go to:
```
http://127.0.0.1:5000
```
(Default Flask Localhost)

## 3. Additional Notes
- Ensure that `uploads/` and `templates/` folders exist before running the project.
- If any package installation fails, ensure Python and pip are updated:
```
python -m pip install --upgrade pip
```
- If you encounter permission issues, try running the commands with `sudo` (for Linux/macOS) or as an administrator (Windows).

## 4. Troubleshooting
### Issue: `ModuleNotFoundError`
**Solution:** Ensure all dependencies are installed with `pip install -r requirements.txt`.

### Issue: `OSError: Address already in use`
**Solution:** Kill the process using the port or change the port in `app1.py` (e.g., `app.run(port=5001)`) or press ctrl + c in VS code terminal

---
This guide should help you set up the project smoothly. If you face any issues, feel free to ask for support!


