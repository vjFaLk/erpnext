cd /home/frappe/frappe-bench
su frappe -c "nohup bench start &"
bench execute erpnext.demo.setup.setup_data.complete_setup