Before running, create the `.env` file.  You can consult `.env.example`.

TO RUN MANUALLY
===============
`poetry run ./main.py`

TO RUN WITH DOCKER-COMPOSE
==========================
To run it in the foreground:
`DOCKER_BUILDKIT=1 docker-compose up`

To run it on the background:
`DOCKER_BUILDKIT=1 docker-compose up -d`


