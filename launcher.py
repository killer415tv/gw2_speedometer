#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GW2 Speedometer Launcher
========================

Launcher unificado para todas las aplicaciones del proyecto GW2 Speedometer.
Permite lanzar fácilmente todas las herramientas desde una interfaz central.

Autor: Mejorado para facilidad de uso
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
        
        # Subtítulo
        subtitle_label = ttk.Label(header_frame,
                                 text="Herramientas profesionales para carreras de escarabajos en Guild Wars 2",
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
        
        # Definir aplicaciones disponibles
        self.apps = [
            {
                'name': '🏎️ Speedometer',
                'description': 'Velocímetro principal con HUD completo, medición de ángulos, aceleración y sistema de checkpoints',
                'file': 'speedometer.py',
                'category': 'Principal',
                'color': self.colors['success']
            },
            {
                'name': '👁️ Visor de Checkpoints',
                'description': 'Visualizador 3D de checkpoints y rutas. Muestra los puntos de control en el mundo 3D',
                'file': 'checkpoints.py',
                'category': 'Visualización',
                'color': self.colors['accent']
            },
            {
                'name': '👻 Sistema Ghost',
                'description': 'Modo fantasma para competir contra tus mejores tiempos. Incluye rankings online',
                'file': 'ghost_online.py',
                'category': 'Competición',
                'color': self.colors['warning']
            },
            {
                'name': '📐 Visualizador de Vectores',
                'description': 'Muestra vectores de dirección, velocidad y ángulos en tiempo real',
                'file': 'vectors.py',
                'category': 'Análisis',
                'color': self.colors['accent']
            },
            {
                'name': '🏁 Creador de Checkpoints (Carreras)',
                'description': 'Herramienta para crear checkpoints personalizados para carreras',
                'file': 'RACINGcheckpointcreator.py',
                'category': 'Herramientas',
                'color': self.colors['secondary']
            },
            {
                'name': '🧗 Creador de Checkpoints (Jumping Puzzles)',
                'description': 'Herramienta para crear checkpoints para jumping puzzles',
                'file': 'JPcheckpointcreator.py',
                'category': 'Herramientas',
                'color': self.colors['secondary']
            },
            {
                'name': '🗺️ Mapa en Tiempo Real',
                'description': 'Visualización de mapa en tiempo real con posición del jugador',
                'file': 'map_realtime.py',
                'category': 'Visualización',
                'color': self.colors['accent']
            },
            {
                'name': '🌐 Mapa Multijugador',
                'description': 'Mapa en tiempo real con soporte multijugador',
                'file': 'map_realtime_multiplayer.py',
                'category': 'Multijugador',
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
        
        # Botón de lanzar
        launch_btn = tk.Button(content_frame,
                             text="Lanzar",
                             bg=app['color'],
                             fg='white',
                             font=('Segoe UI', 8, 'bold'),
                             border=0,
                             padx=15,
                             pady=4,
                             cursor='hand2',
                             command=lambda a=app: self.launch_app(a))
        launch_btn.pack(pady=(0, 5))
        
        # Indicador de estado compacto
        status_label = tk.Label(content_frame,
                              text="● Detenido",
                              bg=self.colors['secondary'],
                              fg=self.colors['text_secondary'],
                              font=('Segoe UI', 7))
        status_label.pack()
        
        # Guardar referencia al status label para actualizaciones
        app['status_label'] = status_label
        
        # Tooltip con descripción completa
        self.create_tooltip(card_frame, app['description'])
        
    def create_tooltip(self, widget, text):
        """Crear tooltip para mostrar descripción completa al pasar el ratón"""
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
            
            tooltip.after(3000, hide_tooltip)  # Auto-hide después de 3 segundos
            widget.tooltip = tooltip
        
        def hide_tooltip(event):
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
        
        widget.bind('<Enter>', show_tooltip)
        widget.bind('<Leave>', hide_tooltip)

    def create_footer(self):
        """Crear el pie de página con información y controles"""
        footer_frame = tk.Frame(self.root, bg=self.colors['secondary'], pady=15)
        footer_frame.pack(fill='x', side='bottom')
        
        # Frame para botones de utilidad
        utils_frame = tk.Frame(footer_frame, bg=self.colors['secondary'])
        utils_frame.pack(pady=(0, 10))
        
        # Botones de utilidad
        buttons = [
            ("🔧 Verificar Dependencias", self.check_dependencies),
            ("📁 Abrir Carpeta Logs", self.open_logs_folder),
            ("📄 Abrir README", self.open_readme),
            ("❌ Cerrar Todo", self.close_all_apps)
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
        
        # Información del proyecto
        info_label = tk.Label(footer_frame,
                            text="GW2 Speedometer Suite v2.06.28 | Herramientas para carreras de escarabajos en Guild Wars 2",
                            bg=self.colors['secondary'],
                            fg=self.colors['text_secondary'],
                            font=('Segoe UI', 8))
        info_label.pack()

    def launch_app(self, app):
        """Lanzar una aplicación específica"""
        try:
            if app['file'] in self.running_processes:
                messagebox.showwarning("Aplicación en Ejecución", 
                                     f"{app['name']} ya está ejecutándose.")
                return
            
            # Verificar que el archivo existe
            app_path = Path(app['file'])
            if not app_path.exists():
                messagebox.showerror("Error", 
                                   f"No se encontró el archivo {app['file']}")
                return
            
            # Lanzar la aplicación en un proceso separado
            process = subprocess.Popen([sys.executable, app['file']], 
                                     cwd=Path.cwd(),
                                     creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
            
            # Guardar referencia al proceso
            self.running_processes[app['file']] = process
            
            # Actualizar estado visual
            app['status_label'].config(text="● Ejecutándose", fg=self.colors['success'])
            
            # Monitorear el proceso
            self.monitor_process(app)
            
            #messagebox.showinfo("Éxito", f"{app['name']} se ha lanzado correctamente.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al lanzar {app['name']}: {str(e)}")

    def monitor_process(self, app):
        """Monitorear el estado de un proceso"""
        def check_process():
            if app['file'] in self.running_processes:
                process = self.running_processes[app['file']]
                if process.poll() is not None:
                    # El proceso ha terminado
                    del self.running_processes[app['file']]
                    app['status_label'].config(text="● Detenido", fg=self.colors['text_secondary'])
                else:
                    # El proceso sigue corriendo, verificar de nuevo en 2 segundos
                    self.root.after(2000, check_process)
        
        # Iniciar monitoreo
        self.root.after(1000, check_process)

    def check_dependencies(self):
        """Verificar que todas las dependencias estén instaladas"""
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
            
            messagebox.showinfo("Dependencias", "✅ Todas las dependencias están instaladas correctamente.")
            
        except ImportError as e:
            messagebox.showerror("Dependencias Faltantes", 
                               f"❌ Faltan dependencias: {str(e)}\n\n"
                               f"Ejecuta 'install.bat' para instalar todas las dependencias.")

    def open_logs_folder(self):
        """Abrir la carpeta de logs"""
        logs_path = Path("logs")
        if logs_path.exists():
            if os.name == 'nt':  # Windows
                os.startfile(logs_path)
            else:  # Unix/Linux/Mac
                subprocess.run(['xdg-open', str(logs_path)])
        else:
            messagebox.showinfo("Carpeta Logs", "La carpeta 'logs' se creará automáticamente cuando ejecutes el speedometer.")

    def open_readme(self):
        """Abrir el archivo README"""
        readme_path = Path("README.md")
        if readme_path.exists():
            if os.name == 'nt':  # Windows
                os.startfile(readme_path)
            else:  # Unix/Linux/Mac
                subprocess.run(['xdg-open', str(readme_path)])
        else:
            messagebox.showwarning("README", "No se encontró el archivo README.md")

    def close_all_apps(self):
        """Cerrar todas las aplicaciones ejecutándose"""
        if not self.running_processes:
            messagebox.showinfo("Sin Aplicaciones", "No hay aplicaciones ejecutándose.")
            return
        
        result = messagebox.askyesno("Cerrar Aplicaciones", 
                                   f"¿Estás seguro de que quieres cerrar {len(self.running_processes)} aplicación(es)?")
        
        if result:
            for app_file, process in list(self.running_processes.items()):
                try:
                    process.terminate()
                    # Dar tiempo para terminar gracefully
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # Si no termina, forzar cierre
                    process.kill()
                except Exception as e:
                    print(f"Error cerrando {app_file}: {e}")
            
            self.running_processes.clear()
            
            # Actualizar estados visuales
            for app in self.apps:
                if 'status_label' in app:
                    app['status_label'].config(text="● Detenido", fg=self.colors['text_secondary'])
            
            messagebox.showinfo("Éxito", "Todas las aplicaciones han sido cerradas.")

    def on_closing(self):
        """Manejar el cierre de la aplicación"""
        if self.running_processes:
            result = messagebox.askyesno("Cerrar Launcher", 
                                       "Hay aplicaciones ejecutándose. ¿Quieres cerrarlas también?")
            if result:
                self.close_all_apps()
        
        self.root.destroy()

    def run(self):
        """Ejecutar el launcher"""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()


def main():
    """Función principal"""
    try:
        # Cambiar al directorio del script
        script_dir = Path(__file__).parent
        os.chdir(script_dir)
        
        # Crear y ejecutar el launcher
        launcher = GW2SpeedometerLauncher()
        launcher.run()
        
    except Exception as e:
        print(f"Error al iniciar el launcher: {e}")
        messagebox.showerror("Error Fatal", f"Error al iniciar el launcher: {e}")


if __name__ == "__main__":
    main() 