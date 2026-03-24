FROM python:3.12-slim
 
WORKDIR /game
 
COPY game.py .
 
ENV TERM=xterm-256color
 
CMD ["python3", "game.py"]
