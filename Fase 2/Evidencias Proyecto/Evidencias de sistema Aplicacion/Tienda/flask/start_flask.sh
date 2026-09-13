#!/bin/bash
# Script para iniciar el servidor Flask

cd /home/tu_usuario/flaskapp
source venv/bin/activate   # si usas entorno virtual
python app.py &

#dar permisos primero
#chmod +x start_flask.sh
