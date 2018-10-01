cd /home/frappe/frappe-bench
su frappe -c "bench execute erpnext.demo.setup.setup_data.complete_setup"
su frappe -c "nohup bench serve &"