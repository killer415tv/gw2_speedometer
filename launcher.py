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
from tkinter import ttk, messagebox, font
import subprocess
import sys
import os
import threading
from pathlib import Path
import json

class GW2SpeedometerLauncher:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("GW2 Speedometer Suite v2.06.28")
        self.root.geometry("950x700")
        self.root.configure(bg='#2c3e50')
        
        # Hacer que la ventana sea redimensionable
        self.root.minsize(800, 600)
        self.root.resizable(True, True)
        
        # Variables para procesos activos
        self.running_processes = {}
        
        # Configurar estilos
        self.setup_styles()
        
        # Crear interfaz
        self.create_header()
        self.create_main_content()
        self.create_footer()
        
        # Verificar dependencias al iniciar
        self.check_dependencies()
        
    def setup_styles(self):
        """Configurar estilos personalizados para la interfaz"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Colores del tema
        self.colors = {
            'bg': '#2c3e50',
            'secondary': '#34495e', 
            'accent': '#3498db',
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'text': '#ecf0f1',
            'text_secondary': '#bdc3c7'
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
        """Crear la cabecera de la aplicación"""
        header_frame = tk.Frame(self.root, bg=self.colors['bg'], pady=20)
        header_frame.pack(fill='x')
        
        # Título principal
        title_label = ttk.Label(header_frame, 
                               text="GW2 Speedometer Suite",
                               style='Header.TLabel')
        title_label.pack()
        
        # Subtitle
        subtitle_label = ttk.Label(header_frame,
                                 text="Professional racing tools for beetle races in Guild Wars 2",
                                 style='Subtitle.TLabel')
        subtitle_label.pack(pady=(5, 0))
        
        # Separator
        separator = ttk.Separator(header_frame, orient='horizontal')
        separator.pack(fill='x', pady=(20, 0))

    def create_main_content(self):
        """Crear el contenido principal con las aplicaciones en cuadrícula"""
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Crear scroll frame con cuadrícula
        canvas = tk.Canvas(main_frame, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg=self.colors['bg'])
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Configurar scroll con rueda del ratón
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
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
                'name': '🧗 Checkpoint Creator (Jumping Puzzles)',
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
        
        # Crear cuadrícula de aplicaciones
        self.create_grid_layout(scrollable_frame, self.apps)
        
        # Configurar grid
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def create_grid_layout(self, parent, apps):
        """Crear una cuadrícula de aplicaciones"""
        # Frame principal para la cuadrícula
        grid_frame = tk.Frame(parent, bg=self.colors['bg'])
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
        # Frame principal de la tarjeta
        card_frame = tk.Frame(parent, bg=self.colors['secondary'], relief='raised', bd=1)
        card_frame.grid(row=row, column=col, padx=8, pady=8, sticky='ew')
        
        # Configurar peso de las columnas para distribución uniforme
        parent.grid_columnconfigure(col, weight=1, uniform="columns")
        
        # Frame de contenido
        content_frame = tk.Frame(card_frame, bg=self.colors['secondary'])
        content_frame.pack(fill='both', expand=True, padx=12, pady=12)
        
        # Emoji y nombre (más grande y prominente)
        name_parts = app['name'].split(' ', 1)
        emoji = name_parts[0] if len(name_parts) > 1 else '🔧'
        name_text = name_parts[1] if len(name_parts) > 1 else app['name']
        
        # Emoji grande
        emoji_label = tk.Label(content_frame,
                              text=emoji,
                              bg=self.colors['secondary'],
                              fg=self.colors['text'],
                              font=('Segoe UI Emoji', 24))
        emoji_label.pack(pady=(0, 5))
        
        # Nombre de la aplicación
        name_label = tk.Label(content_frame,
                            text=name_text,
                            bg=self.colors['secondary'],
                            fg=self.colors['text'],
                            font=('Segoe UI', 9, 'bold'),
                            wraplength=200,
                            justify='center')
        name_label.pack(pady=(0, 5))
        
        # Categoría pequeña
        category_label = tk.Label(content_frame,
                                text=app['category'],
                                bg=self.colors['secondary'],
                                fg=self.colors['text_secondary'],
                                font=('Segoe UI', 7),
                                justify='center')
        category_label.pack(pady=(0, 8))
        
        # Launch button
        launch_btn = tk.Button(content_frame,
                             text="Launch",
                             bg=self.colors['accent'],
                             fg='white',
                             font=('Segoe UI', 8, 'bold'),
                             border=0,
                             padx=15,
                             pady=4,
                             cursor='hand2',
                             command=lambda a=app: self.launch_app(a))
        launch_btn.pack(pady=(0, 5))
        
        # Compact status indicator
        status_label = tk.Label(content_frame,
                              text="● Stopped",
                              bg=self.colors['secondary'],
                              fg=self.colors['text_secondary'],
                              font=('Segoe UI', 7))
        status_label.pack()
        
        # Guardar referencia al status label para actualizaciones
        app['status_label'] = status_label
        
        # Tooltip with complete description
        self.create_tooltip(card_frame, app['description'])
        
    def create_tooltip(self, widget, text):
        """Create tooltip to show complete description on mouse hover"""
        def show_tooltip(event):
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root+10}+{event.y_root+10}")
            
            label = tk.Label(tooltip, text=text, 
                           bg='#2c3e50', fg='white',
                           font=('Segoe UI', 9),
                           wraplength=300,
                           justify='left',
                           padx=8, pady=6)
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
        """Create footer with information and controls"""
        footer_frame = tk.Frame(self.root, bg=self.colors['secondary'], pady=15)
        footer_frame.pack(fill='x', side='bottom')
        
        # Frame for utility buttons
        utils_frame = tk.Frame(footer_frame, bg=self.colors['secondary'])
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
        info_label = tk.Label(footer_frame,
                            text="GW2 Speedometer Suite v2.06.28 | Professional tools for beetle racing in Guild Wars 2",
                            bg=self.colors['secondary'],
                            fg=self.colors['text_secondary'],
                            font=('Segoe UI', 8))
        info_label.pack()

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
            
            # Monitor process
            self.monitor_process(app)
            
            #messagebox.showinfo("Success", f"{app['name']} launched successfully.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error launching {app['name']}: {str(e)}")

    def monitor_process(self, app):
        """Monitor process status"""
        def check_process():
            if app['file'] in self.running_processes:
                process = self.running_processes[app['file']]
                if process.poll() is not None:
                    # Process has terminated
                    del self.running_processes[app['file']]
                    app['status_label'].config(text="● Stopped", fg=self.colors['text_secondary'])
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
            import paho.mqtt.client
            import PySide2
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