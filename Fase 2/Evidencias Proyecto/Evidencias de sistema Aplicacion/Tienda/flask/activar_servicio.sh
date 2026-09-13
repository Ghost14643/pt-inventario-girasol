sudo systemctl daemon-reload
sudo systemctl enable flaskapp.service
sudo systemctl start flaskapp.service



sudo systemctl status flaskapp.service
sudo journalctl -u flaskapp.service -f
