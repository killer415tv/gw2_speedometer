#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GW2 Speedometer Launcher
========================

Unified launcher for all GW2 Speedometer project applications.
Easily launch all tools from a central interface.

Author: Enhanced for ease of use
"""

import tkinter as tk
from tkinter import ttk, messagebox, font, Canvas
from tkinter.font import Font
import subprocess
import sys
import os
import threading
from pathlib import Path
import json
import webbrowser
# PIL y cairosvg se importan dinámicamente en load_logo() para evitar errores si no están instaladas

class GW2SpeedometerLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Beetlerank Speed Suite v6.00.00")
        self.root.geometry("950x650")  # Reducir altura para que quepa todo
        self.root.configure(bg='#1a1a1a')
        
        # Crear gradiente de fondo
        self.create_gradient_background()
        
        # Hacer que la ventana sea redimensionable
        self.root.minsize(800, 600)
        self.root.resizable(True, True)
        
        # Variables para procesos activos
        self.running_processes = {}
        
        # Configurar estilos
        self.setup_styles()
        
        # Cargar logo
        self.load_logo()
        
        # Crear interfaz
        self.create_header()
        self.create_main_content()
        self.create_footer()
        
        # Verificar dependencias al iniciar
        self.check_dependencies()
    
    def create_gradient_background(self):
        """Create gradient background effect"""
        # Create main background - the sections will handle their own colors
        # for the gradient effect
        pass
        
    def load_logo(self):
        """Load the Beetlerank logo (PNG format)"""
        self.logo_img = None
        try:
            # Check if PNG logo exists first
            logo_path = Path("logo.png")
            if logo_path.exists():
                self.logo_img = tk.PhotoImage(file=str(logo_path))
                return
            
            # Fallback to SVG if PNG doesn't exist (requires dependencies)
            logo_svg_path = Path("logo.svg") 
            if logo_svg_path.exists():
                try:
                    import cairosvg
                    from PIL import Image, ImageTk
                    from io import BytesIO
                    
                    # Convert SVG to PNG
                    png_output = cairosvg.svg2png(url=str(logo_svg_path), output_width=180, output_height=40)
                    
                    # Load PNG into PIL and convert for tkinter
                    logo_image = Image.open(BytesIO(png_output))
                    self.logo_img = ImageTk.PhotoImage(logo_image)
                except ImportError:
                    # Dependencies not available - continue without logo
                    pass
                    
        except Exception as e:
            # Any error - continue without logo
            print(f"Logo loading failed: {e}")
            pass
        
    def setup_styles(self):
        """Configurar estilos personalizados para la interfaz"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Beetlerank.com color scheme with gradient support
        self.colors = {
            'bg': '#1a1a1a',           # Dark background like beetlerank  
            'header_bg': '#151515',     # Darker for header
            'main_bg': '#1a1a1a',       # Main content background
            'footer_bg': '#202020',     # Lighter for footer
            'secondary': '#2d2d2d',     # Dark gray for cards
            'accent': '#e74c3c',        # Red accent like beetlerank
            'success': '#27ae60',       # Keep green for success
            'warning': '#f39c12',       # Keep orange for warnings
            'danger': '#c0392b',        # Darker red for errors
            'text': '#ffffff',          # Pure white text
            'text_secondary': '#999999', # Gray secondary text
            'border': '#404040'         # Gray borders
        }
        
        # Configurar estilos personalizados
        self.style.configure('Header.TLabel', 
                           background=self.colors['bg'],
                           foreground=self.colors['text'],
                           font=('Segoe UI', 20, 'bold'))
        
        self.style.configure('Subtitle.TLabel',
                           background=self.colors['bg'],
                           foreground=self.colors['text_secondary'],
                           font=('Segoe UI', 10))
        
        self.style.configure('AppButton.TButton',
                           font=('Segoe UI', 10, 'bold'),
                           padding=(20, 10))
        
        self.style.configure('Status.TLabel',
                           background=self.colors['bg'],
                           foreground=self.colors['text_secondary'],
                           font=('Segoe UI', 9))

    def create_header(self):
        """Create compact header with Beetlerank branding"""
        header_frame = tk.Frame(self.root, bg=self.colors['header_bg'], pady=15)
        header_frame.pack(fill='x')
        
        # Logo and title in single row
        top_row = tk.Frame(header_frame, bg=self.colors['header_bg'])
        top_row.pack(pady=(0, 8))
        
        # Logo (smaller)
        if hasattr(self, 'logo_img') and self.logo_img:
            logo_label = tk.Label(top_row, image=self.logo_img, bg=self.colors['header_bg'])
            logo_label.pack(side='left', padx=(0, 15))
        
        # Title container
        title_frame = tk.Frame(top_row, bg=self.colors['header_bg'])
        title_frame.pack(side='left')
        
        # "Beetlerank Speed Suite" in one line
        title_line1 = tk.Frame(title_frame, bg=self.colors['header_bg'])
        title_line1.pack()
        
        beetlerank_label = tk.Label(title_line1, 
                                   text="BEETLERANK",
                                   bg=self.colors['header_bg'],
                                   fg=self.colors['accent'],
                                   font=('Segoe UI', 18, 'bold'))
        beetlerank_label.pack(side='left')
        
        suite_label = tk.Label(title_line1,
                              text=" SPEED SUITE",
                              bg=self.colors['header_bg'],
                              fg=self.colors['text'],
                              font=('Segoe UI', 18, 'bold'))
        suite_label.pack(side='left')
        
        # Compact subtitle with link
        subtitle_frame = tk.Frame(title_frame, bg=self.colors['header_bg'])
        subtitle_frame.pack()
        
        subtitle_label = tk.Label(subtitle_frame,
                                text="Professional beetle racing tools • ",
                                bg=self.colors['header_bg'],
                                fg=self.colors['text_secondary'],
                                font=('Segoe UI', 9))
        subtitle_label.pack(side='left')
        
        link_label = tk.Label(subtitle_frame,
                            text="beetlerank.com",
                            bg=self.colors['header_bg'],
                            fg=self.colors['accent'],
                            font=('Segoe UI', 9, 'underline'),
                            cursor='hand2')
        link_label.pack(side='left')
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://beetlerank.com"))
        
        # Thin separator line
        separator = tk.Frame(header_frame, bg=self.colors['accent'], height=1)
        separator.pack(fill='x', pady=(8, 0))

    def create_main_content(self):
        """Create compact grid layout for applications"""
        main_frame = tk.Frame(self.root, bg=self.colors['main_bg'])
        main_frame.pack(expand=True, fill='both', padx=15, pady=10)
        
        # Define available applications
        self.apps = [
            {
                'name': '🏎️ Speedometer',
                'description': 'Main speedometer with complete HUD, angle measurement, acceleration and checkpoint system',
                'file': 'speedometer.py',
                'category': 'Main',
                'color': self.colors['success']
            },
            {
                'name': '👁️ Checkpoint Viewer',
                'description': '3D checkpoint and route visualizer. Shows control points in the 3D world',
                'file': 'checkpoints.py',
                'category': 'Visualization',
                'color': self.colors['accent']
            },
            {
                'name': '👻 Ghost System',
                'description': 'Ghost mode to compete against your best times. Includes online rankings',
                'file': 'ghost_online.py',
                'category': 'Competition',
                'color': self.colors['warning']
            },
            {
                'name': '📐 Vector Visualizer',
                'description': 'Shows direction vectors, velocity and angles in real time',
                'file': 'vectors.py',
                'category': 'Analysis',
                'color': self.colors['accent']
            },
            {
                'name': '🏁 Checkpoint Creator (Racing)',
                'description': 'Tool to create custom checkpoints for racing',
                'file': 'RACINGcheckpointcreator.py',
                'category': 'Tools',
                'color': self.colors['secondary']
            },
            {
                'name': '🧗 Checkpoint Creator (Jumping)',
                'description': 'Tool to create checkpoints for jumping puzzles',
                'file': 'JPcheckpointcreator.py',
                'category': 'Tools',
                'color': self.colors['secondary']
            },
            {
                'name': '🗺️ Real-time Map',
                'description': 'Real-time map visualization with player position',
                'file': 'map_realtime.py',
                'category': 'Visualization',
                'color': self.colors['accent']
            },
            {
                'name': '🌐 Multiplayer Map',
                'description': 'Real-time map with multiplayer support',
                'file': 'map_realtime_multiplayer.py',
                'category': 'Multiplayer',
                'color': self.colors['warning']
            }
        ]
        
        # Crear cuadrícula directa sin scroll (más simple)
        self.create_grid_layout(main_frame, self.apps)

    def create_grid_layout(self, parent, apps):
        """Create grid layout for applications"""
        # Frame principal para la cuadrícula
        grid_frame = tk.Frame(parent, bg=self.colors['main_bg'])
        grid_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Calcular número de columnas basado en el número de apps
        total_apps = len(apps)
        if total_apps <= 6:
            cols = 3
        elif total_apps <= 12:
            cols = 4  
        else:
            cols = 4  # Máximo 4 columnas
        
        # Crear tarjetas en cuadrícula
        for idx, app in enumerate(apps):
            row = idx // cols
            col = idx % cols
            self.create_app_card_grid(grid_frame, app, row, col)

    def create_app_card_grid(self, parent, app, row, col):
        """Crear una tarjeta compacta para cuadrícula"""
        # Frame principal de la tarjeta con bordes sutiles
        card_frame = tk.Frame(parent, bg=self.colors['secondary'], 
                             relief='solid', bd=1, highlightbackground=self.colors['border'],
                             highlightcolor=self.colors['border'], highlightthickness=1)
        card_frame.grid(row=row, column=col, padx=6, pady=6, sticky='ew')
        
        # Configurar peso de las columnas para distribución uniforme
        parent.grid_columnconfigure(col, weight=1, uniform="columns")
        
        # Frame de contenido compacto
        content_frame = tk.Frame(card_frame, bg=self.colors['secondary'])
        content_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Emoji y nombre (más grande y prominente)
        name_parts = app['name'].split(' ', 1)
        emoji = name_parts[0] if len(name_parts) > 1 else '🔧'
        name_text = name_parts[1] if len(name_parts) > 1 else app['name']
        
        # Emoji compacto
        emoji_label = tk.Label(content_frame,
                              text=emoji,
                              bg=self.colors['secondary'],
                              fg=self.colors['text'],
                              font=('Segoe UI Emoji', 20))
        emoji_label.pack(pady=(0, 3))
        
        # Nombre de la aplicación
        name_label = tk.Label(content_frame,
                            text=name_text,
                            bg=self.colors['secondary'],
                            fg=self.colors['text'],
                            font=('Segoe UI', 8, 'bold'),
                            wraplength=180,
                            justify='center')
        name_label.pack(pady=(0, 2))
        
        # Categoría pequeña
        category_label = tk.Label(content_frame,
                                text=app['category'],
                                bg=self.colors['secondary'],
                                fg=self.colors['text_secondary'],
                                font=('Segoe UI', 6),
                                justify='center')
        category_label.pack(pady=(0, 5))
        
        # Action button compacto (cambia entre Launch y Close)
        action_btn = tk.Button(content_frame,
                             text="Launch",
                             bg=self.colors['accent'],
                             fg='white',
                             font=('Segoe UI', 7, 'bold'),
                             border=0,
                             padx=12,
                             pady=3,
                             cursor='hand2',
                             command=lambda a=app: self.launch_app(a))
        action_btn.pack(pady=(0, 3))
        
        # Status indicator compacto
        status_label = tk.Label(content_frame,
                              text="● Stopped",
                              bg=self.colors['secondary'],
                              fg=self.colors['text_secondary'],
                              font=('Segoe UI', 6))
        status_label.pack()
        
        # Guardar referencias para actualizaciones
        app['status_label'] = status_label
        app['action_btn'] = action_btn
        
        # Tooltip with complete description
        self.create_tooltip(card_frame, app['description'])
        
    def create_tooltip(self, widget, text):
        """Create tooltip to show complete description on mouse hover"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = tk.Label(tooltip, text=text, 
                           bg=self.colors['secondary'], fg=self.colors['text'],
                           font=('Segoe UI', 9),
                           wraplength=300,
                           justify='left',
                           padx=8, pady=6,
                           relief='solid', bd=1,
                           highlightbackground=self.colors['border'])
            label.pack()
            
            def hide_tooltip():
                tooltip.destroy()
            
            tooltip.after(3000, hide_tooltip)  # Auto-hide after 3 seconds
            widget.tooltip = tooltip
        
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
        
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)

    def create_footer(self):
        """Create compact footer with information and controls"""
        footer_frame = tk.Frame(self.root, bg=self.colors['footer_bg'], pady=10)
        footer_frame.pack(fill='x', side='bottom')
        
        # Frame for utility buttons
        utils_frame = tk.Frame(footer_frame, bg=self.colors['footer_bg'])
        utils_frame.pack(pady=(0, 10))
        
        # Utility buttons
        buttons = [
            ("🔧 Check Dependencies", self.check_dependencies),
            ("📁 Open Logs Folder", self.open_logs_folder),
            ("📄 Open README", self.open_readme),
            ("❌ Close All", self.close_all_apps)
        ]
        
        for text, command in buttons:
            btn = tk.Button(utils_frame,
                          text=text,
                          bg=self.colors['accent'],
                          fg='white',
                          font=('Segoe UI', 9),
                          border=0,
                          padx=15,
                          pady=5,
                          cursor='hand2',
                          command=command)
            btn.pack(side='left', padx=5)
        
        # Project information
        info_frame = tk.Frame(footer_frame, bg=self.colors['footer_bg'])
        info_frame.pack()
        
        info_label = tk.Label(info_frame,
                            text="Beetlerank Speed Suite v6.00.00 | Powered by ",
                            bg=self.colors['footer_bg'],
                            fg=self.colors['text_secondary'],
                            font=('Segoe UI', 8))
        info_label.pack(side='left')
        
        # Clickable beetlerank.com link in footer
        beetlerank_link = tk.Label(info_frame,
                                 text="beetlerank.com",
                                 bg=self.colors['footer_bg'],
                                 fg=self.colors['accent'],
                                 font=('Segoe UI', 8, 'underline'),
                                 cursor='hand2')
        beetlerank_link.pack(side='left')
        beetlerank_link.bind("<Button-1>", lambda e: webbrowser.open("https://beetlerank.com"))

    def launch_app(self, app):
        """Launch a specific application"""
        try:
            if app['file'] in self.running_processes:
                messagebox.showwarning("Application Running",
                                     f"{app['name']} is already running.")
                return
            
            # Check if file exists
            app_path = Path(app['file'])
            if not app_path.exists():
                messagebox.showerror("Error",
                                   f"File {app['file']} not found")
                return
            
            # Launch application in separate process
            process = subprocess.Popen([sys.executable, app['file']],
                                     cwd=Path.cwd(),
                                     creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            
            # Save process reference
            self.running_processes[app['file']] = process
            
            # Update visual status
            app['status_label'].config(text="● Running", fg=self.colors['success'])
            
            # Change button to Close
            app['action_btn'].config(text="Close",
                                    bg=self.colors['danger'],
                                    command=lambda a=app: self.close_app(a))
            
            # Monitor process
            self.monitor_process(app)
            
            #messagebox.showinfo("Success", f"{app['name']} launched successfully.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error launching {app['name']}: {str(e)}")
    
    def close_app(self, app):
        """Close a specific application"""
        try:
            if app['file'] not in self.running_processes:
                messagebox.showwarning("Not Running",
                                     f"{app['name']} is not running.")
                return
            
            process = self.running_processes[app['file']]
            
            # Terminate the process
            try:
                process.terminate()
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # If it doesn't terminate, force kill
                process.kill()
            
            # Remove from running processes
            del self.running_processes[app['file']]
            
            # Update visual status
            app['status_label'].config(text="● Stopped", fg=self.colors['text_secondary'])
            
            # Change button back to Launch
            app['action_btn'].config(text="Launch",
                                    bg=self.colors['accent'],
                                    command=lambda a=app: self.launch_app(a))
            
        except Exception as e:
            messagebox.showerror("Error", f"Error closing {app['name']}: {str(e)}")

    def monitor_process(self, app):
        """Monitor process status"""
        def check_process():
            if app['file'] in self.running_processes:
                process = self.running_processes[app['file']]
                if process.poll() is not None:
                    # Process has terminated
                    del self.running_processes[app['file']]
                    app['status_label'].config(text="● Stopped", fg=self.colors['text_secondary'])
                    # Change button back to Launch
                    app['action_btn'].config(text="Launch",
                                            bg=self.colors['accent'],
                                            command=lambda a=app: self.launch_app(a))
                else:
                    # Process still running, check again in 2 seconds
                    self.root.after(2000, check_process)
        
        # Start monitoring
        self.root.after(1000, check_process)

    def check_dependencies(self):
        """Check if all dependencies are installed"""
        try:
            import pandas
            import numpy
            import scipy
            import pynput
            import PySide6
            import pyqtgraph
            import requests
            import websocket
            
            messagebox.showinfo("Dependencies", "✅ All dependencies are installed correctly.")
            
        except ImportError as e:
            messagebox.showerror("Missing Dependencies", 
                               f"❌ Missing dependencies: {str(e)}\n\n"
                               f"Run 'install.bat' to install all dependencies.")

    def open_logs_folder(self):
        """Open logs folder"""
        logs_path = Path("logs")
        if logs_path.exists():
            if os.name == 'nt':  # Windows
                os.startfile(logs_path)
            else:  # Unix/Linux/Mac
                subprocess.run(['xdg-open', str(logs_path)])
        else:
            messagebox.showinfo("Logs Folder", "The 'logs' folder will be created automatically when you run the speedometer.")

    def open_readme(self):
        """Open README file"""
        readme_path = Path("README.md")
        if readme_path.exists():
            if os.name == 'nt':  # Windows
                os.startfile(readme_path)
            else:  # Unix/Linux/Mac
                subprocess.run(['xdg-open', str(readme_path)])
        else:
            messagebox.showwarning("README", "README.md file not found")

    def close_all_apps(self):
        """Close all running applications"""
        if not self.running_processes:
            messagebox.showinfo("No Applications", "No applications are running.")
            return
        
        result = messagebox.askyesno("Close Applications", 
                                   f"Are you sure you want to close {len(self.running_processes)} application(s)?")
        
        if result:
            for app_file, process in list(self.running_processes.items()):
                try:
                    process.terminate()
                    # Give time to terminate gracefully
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # If it doesn't terminate, force kill
                    process.kill()
                except Exception as e:
                    print(f"Error closing {app_file}: {e}")
            
            self.running_processes.clear()
            
            # Update visual states
            for app in self.apps:
                if 'status_label' in app:
                    app['status_label'].config(text="● Stopped", fg=self.colors['text_secondary'])
                # Change button back to Launch
                if 'action_btn' in app:
                    app['action_btn'].config(text="Launch",
                                            bg=self.colors['accent'],
                                            command=lambda a=app: self.launch_app(a))
            
            messagebox.showinfo("Success", "All applications have been closed.")

    def on_closing(self):
        """Handle application closure"""
        if self.running_processes:
            result = messagebox.askyesno("Close Launcher", 
                                       "There are applications running. Do you want to close them too?")
            if result:
                self.close_all_apps()
        
        self.root.destroy()

    def run(self):
        """Run the launcher"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


def main():
    """Main function"""
    try:
        # Change to script directory
        script_dir = Path(__file__).parent
        os.chdir(script_dir)
        
        # Create and run launcher
        launcher = GW2SpeedometerLauncher()
        launcher.run()
        
    except Exception as e:
        print(f"Error starting launcher: {e}")
        messagebox.showerror("Fatal Error", f"Error starting launcher: {e}")


if __name__ == "__main__":
    main() 