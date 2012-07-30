#!/bin/bash
add-apt-repository ppa:nginx/stable
apt-get -y update 
apt-get -y install nginx




cat > "/etc/nginx/sites-available/thedayexperiment.com" << EOF
server {
        #listen   80; ## listen for ipv4; this line is default and implied
        #listen   [::]:80 default ipv6only=on; ## listen for ipv6

        root /srv/igotoo/create/;
        index index.html index.htm;

        # Make site accessible from http://localhost/
        server_name localhost;

        location /media/{
           alias /srv/igotooserver/igotooserver/media/;
        }

        location /api/ {
            uwsgi_pass unix://opt/run/www-data/igt.sock;
            include uwsgi_params;
        }


}
EOF

sudo rm -rf /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/igotoo.com /etc/nginx/sites-enabled/igotoo.com
/etc/init.d/nginx start
