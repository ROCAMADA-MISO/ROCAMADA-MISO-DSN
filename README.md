# Desarrollo de Software en la Nube

### Integrantes
- Roberto Parra
- Camilo Sanchez
- Daniela Castellanos
- Manuel Bello

## Instrucciones de ejecución
### Desarrollo
Ejecutar `docker-compose -f docker-compose.dev.yml up` sobre la raíz del proyecto. Esto levantará la base de datos y la instancia de redis utilizada en conjunto con celery para el procesamiento asíncrono de archivos.

Adicionalmente, ejecutar `flask --app app.py --debug run` adentro del directorio del microservicio (o los microservicios) deseados para su ejecución de manera local.

**NOTA:** *Para cambiar el puerto de ejecución de los microservicios, cambiar la variable de entorno FLASK_RUN_PORT en los archivos de variables de entorno `.env`*

### Despliegue
Ejecutar `docker-compose build` y luego `docker-compose up` sobre la raíz del proyecto. Esto levantará los servidores WSGI Gunicorn junto con nginx para el procesamiento y redireccionamiento de peticiones.

Si se desea ejecutar únicamente algún archivo de docker-compose, ejecutar el siguiente comando `docker-compose -f <file_name> <command>`