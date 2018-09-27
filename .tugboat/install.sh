# Set noninteractive and set mariadb password
export DEBIAN_FRONTEND=noninteractive
sudo debconf-set-selections <<< 'mariadb-server-10.2 mysql-server/root_password password frappe'
sudo debconf-set-selections <<< 'mariadb-server-10.2 mysql-server/root_password_again password frappe'

sudo apt-get update
sudo apt-get install software-properties-common python-pip python-dev

# MariaDB Repo
sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xF1656F24C74CD1D8
sudo add-apt-repository 'deb [arch=amd64,i386,ppc64el] http://ftp.ubuntu-tw.org/mirror/mariadb/repo/10.2/ubuntu xenial main'

# Yarn Repo
curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | sudo apt-key add -
echo "deb https://dl.yarnpkg.com/debian/ stable main" | sudo tee /etc/apt/sources.list.d/yarn.list

# NodeJS Repo
curl -sL https://deb.nodesource.com/setup_8.x | sudo -E bash -

# Install packages
sudo apt-get install -y git redis-server mariadb-server-10.2 libmysqlclient-dev nodejs yarn

# Configure MariaDB
sudo cp .tugboat/mysql.conf /etc/mysql/conf.d/mariadb.cnf
sudo service mysql restart

# Install bench package and init bench folder
cd ~/
git clone https://github.com/frappe/bench .bench
sudo pip install ./.bench

# Create frappe user and go to frappe home
sudo useradd -ms /bin/bash frappe
cd /home/frappe/

su frappe -c "bench init frappe-bench"

## Create site and set it as default
cd /home/frappe/frappe-bench
su frappe -c "bench new-site site1.local --mariadb-root-password frappe --admin-password frappe"
su frappe -c "bench use site1.local"