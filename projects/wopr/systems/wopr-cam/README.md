**wopr-cam** - Camera service 

- Flask API, port 5000
- EMEET SmartCam C960 4K
- Endpoint: POST /capture
- Saves to NFS, returns image path
- Systemd service, runs as wopr user
- 3D printed overhead mount