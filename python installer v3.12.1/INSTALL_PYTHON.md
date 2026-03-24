# Python Installation Guide

## ⚠️ IMPORTANT: Add Python to PATH

When installing Python, you **MUST** check the box that says:

```
☑ Add Python to PATH
```

This is **critical** for the Beetlerank Speed Suite to work properly!

## Installation Steps

1. **Download Python**
   - Use the installers in this folder:
     - `python-3.12.1-amd64.exe` (64-bit recommended)
     - `python-3.12.1.exe` (32-bit - only if 64-bit doesn't work)

2. **Run the Installer**

3. **IMPORTANT: Select "Add Python to PATH"**
   ```
   ☑ Add Python to PATH
   ```
   
   If you don't see this option, click on "Customize installation" first.

4. **Complete the installation**
   - Click "Install Now" or customize if you prefer
   - Wait for installation to finish
   - Click "Close" when done

5. **Verify Installation**
   - Open a new Command Prompt (cmd)
   - Type: `python --version`
   - You should see: `Python 3.12.1`

## Troubleshooting

### "python is not recognized" error
- Python was not added to PATH during installation
- Re-run the installer and select "Modify"
- Check "Add Python to PATH" and complete

### Need to add Python to PATH manually
1. Search Windows for "Environment Variables"
2. Click "Edit the system environment variables"
3. Click "Environment Variables"
4. Under "System variables", find "Path" and click "Edit"
5. Click "New" and add these two paths:
   - `C:\Users\YOUR_USERNAME\AppData\Local\Programs\Python\Python312`
   - `C:\Users\YOUR_USERNAME\AppData\Local\Programs\Python\Python312\Scripts`
6. Replace "YOUR_USERNAME" with your Windows username

## After Python is Installed

Run `install.bat` from the main folder to complete the setup!