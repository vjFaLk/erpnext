#!/bin/bash

cd ~/
curl -I https://github.com/digithinkit/frappe/tree/$TRAVIS_BRANCH | head -n 1 | cut -d $' ' -f2 | (
	read response;
	[ $response == '200' ] && branch=$TRAVIS_BRANCH || branch='bloomstack-staging';
	bench init frappe-bench --frappe-path https://github.com/digithinkit/frappe.git --frappe-branch $branch --python $(which python)
)
