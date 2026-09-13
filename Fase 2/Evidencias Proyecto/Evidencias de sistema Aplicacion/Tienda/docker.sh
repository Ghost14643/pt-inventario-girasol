docker run -d \
--name mint_fb \
-p 3050:3050 \
-v /home/data:/data \
--tmpfs /tmp:rw,size=512m \
--restart unless-stopped \
mint_firebird:latest \
/bin/bash -c "mkdir -p /tmp/firebird && chmod 1777 /tmp/firebird && /opt/firebird/bin/fbserver -daemon && tail -f /dev/null"