# -*- coding: utf-8 -*-
# Copyright (c) 2017, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import datetime

import frappe
from frappe import _
from frappe.contacts.doctype.address.address import get_address_display
from frappe.model.document import Document
from frappe.utils import cstr, get_datetime, get_link_to_form, getdate
from frappe.utils.user import get_user_fullname


class DeliveryTrip(Document):
	def on_submit(self):
		self.update_delivery_notes()

	def on_cancel(self):
		self.update_delivery_notes(delete=True)

	def update_delivery_notes(self, delete=False):
		delivery_notes = list(set([stop.delivery_note for stop in self.delivery_stops if stop.delivery_note]))

		update_fields = {
			"transporter": self.driver,
			"transporter_name": self.driver_name,
			"transport_mode": "Road",
			"vehicle_no": self.vehicle,
			"vehicle_type": "Regular",
			"lr_no": self.name,
			"lr_date": self.date
		}

		for delivery_note in delivery_notes:
			note_doc = frappe.get_doc("Delivery Note", delivery_note)

			for field, value in update_fields.items():
				value = None if delete else value
				setattr(note_doc, field, value)

			note_doc.save()
			
		delivery_notes = [get_link_to_form("Delivery Note", note) for note in delivery_notes]
		frappe.msgprint(_("Delivery Notes {0} updated".format(", ".join(delivery_notes))))

	def form_route_list(self, optimize):
		"""
		Form a list of address routes based on the delivery stops. If locks
		are present, and the routes need to be optimized, then they will be
		split into sublists at the specified lock position(s).

		Args:
			optimize [bool]: True if route needs to be optimized, else False

		Returns:
			[list of list of str]: List of address routes split at locks, if optimize is True
		"""

		settings = frappe.get_single("Google Maps Settings")
		home_address = get_address_display(frappe.get_doc("Address", settings.home_address).as_dict())

		route_list = []
		# Initialize first leg with origin as the home address
		leg = [home_address]

		for stop in self.delivery_stops:
			leg.append(stop.customer_address)

			if optimize and stop.lock:
				route_list.append(leg)
				leg = [stop.customer_address]

		# For last leg, append home address as the destination
		# only if lock isn"t on the final stop
		if len(leg) > 1:
			leg.append(home_address)
			route_list.append(leg)

		return route_list

	def rearrange_stops(self, optimized_order, start):
		"""
		Re-arrange delivery stops based on order optimized
		for vehicle routing problems.

		Args:
			optimized_order [list of int]: The index-based optimized order of the route
			start [int]: The index at which to start the rearrangement
		"""

		stops_order = []

		# Child table idx starts at 1
		for new_idx, old_idx in enumerate(optimized_order, 1):
			new_idx = start + new_idx
			old_idx = start + old_idx

			self.delivery_stops[old_idx].idx = new_idx
			stops_order.append(self.delivery_stops[old_idx])

		self.delivery_stops[start:start + len(stops_order)] = stops_order


@frappe.whitelist()
def get_contact_and_address(name):
	out = frappe._dict()
	get_default_contact(out, name)
	get_default_address(out, name)
	return out


def get_default_contact(out, name):
	contact_persons = frappe.db.sql(
			"""
			select parent,
				(select is_primary_contact from tabContact c where c.name = dl.parent) as is_primary_contact
			from
				`tabDynamic Link` dl
			where
				dl.link_doctype="Customer"
				and dl.link_name=%s
				and dl.parenttype = "Contact"
		""", (name), as_dict=1)

	if contact_persons:
		for out.contact_person in contact_persons:
			if out.contact_person.is_primary_contact:
				return out.contact_person

		out.contact_person = contact_persons[0]

		return out.contact_person


def get_default_address(out, name):
	shipping_addresses = frappe.db.sql(
			"""
			select parent,
				(select is_shipping_address from tabAddress a where a.name=dl.parent) as is_shipping_address
			from
				`tabDynamic Link` dl
			where
				dl.link_doctype="Customer"
				and dl.link_name=%s
				and dl.parenttype = "Address"
		""", (name), as_dict=1)

	if shipping_addresses:
		for out.shipping_address in shipping_addresses:
			if out.shipping_address.is_shipping_address:
				return out.shipping_address

		out.shipping_address = shipping_addresses[0]

		return out.shipping_address


@frappe.whitelist()
def get_contact_display(contact):
	contact_info = frappe.db.get_value(
		"Contact", contact,
		["first_name", "last_name", "phone", "mobile_no"],
		as_dict=1)

	contact_info.html = """ <b>%(first_name)s %(last_name)s</b> <br> %(phone)s <br> %(mobile_no)s""" % {
		"first_name": contact_info.first_name,
		"last_name": contact_info.last_name or "",
		"phone": contact_info.phone or "",
		"mobile_no": contact_info.mobile_no or ""
	}

	return contact_info.html


@frappe.whitelist()
def optimize_route(delivery_trip):
	process_route(delivery_trip, optimize=True)


@frappe.whitelist()
def get_arrival_times(delivery_trip):
	process_route(delivery_trip, optimize=False)


def process_route(delivery_trip, optimize):
	"""
	Estimate the arrival times for each stop in the Delivery Trip.
	If `optimize` is True, the stops will be re-arranged, based
	on the optimized order, before estimating the arrival times.

	Args:
		delivery_trip [str]: Name of the Delivery Trip document
		optimize [bool]: True if route needs to be optimized, else False
	"""

	delivery_trip = frappe.get_doc("Delivery Trip", delivery_trip)

	departure_datetime = get_datetime(delivery_trip.departure_time)
	route_list = delivery_trip.form_route_list(optimize)

	# For locks, maintain idx count while looping through route list
	idx = 0
	for route in route_list:
		directions = get_directions(route, departure_datetime, optimize)

		if directions:
			if optimize and len(directions.get("waypoint_order")) > 1:
				delivery_trip.rearrange_stops(directions.get("waypoint_order"), start=idx)

			# Avoid estimating last leg back to the home address
			legs = directions.get("legs")[:-1] if route == route_list[-1] else directions.get("legs")

			# Google Maps returns the legs in the optimized order
			for leg in legs:
				duration = leg.get("duration").get("value")

				estimated_arrival = get_rounded_time(departure_datetime + datetime.timedelta(seconds=duration))
				delivery_trip.delivery_stops[idx].estimated_arrival = estimated_arrival

				departure_datetime = estimated_arrival
				idx += 1
		else:
			idx += len(route) - 1

	delivery_trip.save()


def get_directions(route, departure_time, optimize):
	"""
	Retrieve map directions for a given route and departure time.
	If optimize is true, Google Maps will return an optimized
	order for the intermediate waypoints.

	Args:
		departure_time [object]: Departure time for the route (datetime.datetime)
		route [list of str]: Route addresses (origin -> waypoint(s), if any -> destination)
		optimize [bool]: True if route needs to be optimized, else False

	Returns:
		[dict]: Route legs and, if `optimize` is True, optimized waypoint order
	"""

	settings = frappe.get_single("Google Maps Settings")
	maps_client = settings.get_client()

	directions_data = {
		"origin": route[0],
		"destination": route[-1],
		"waypoints": route[1: -1],
		"optimize_waypoints": optimize,
		"departure_time": departure_time
	}

	try:
		directions = maps_client.directions(**directions_data)
	except Exception as e:
		frappe.throw(_(e.message))

	return directions[0] if directions else False


def get_rounded_time(arrival_datetime):
	discard = datetime.timedelta(minutes=arrival_datetime.minute % 10,
								seconds=arrival_datetime.second,
								microseconds=arrival_datetime.microsecond)

	arrival_datetime -= discard

	if discard >= datetime.timedelta(minutes=5):
		arrival_datetime += datetime.timedelta(minutes=10)

	return arrival_datetime


@frappe.whitelist()
def notify_customers(docname, date, driver, vehicle, sender_email, delivery_notification):
	sender_name = get_user_fullname(sender_email)
	attachments = []

	parent_doc = frappe.get_doc('Delivery Trip', docname)
	args = parent_doc.as_dict()

	for delivery_stop in parent_doc.delivery_stops:
		contact_info = frappe.db.get_value("Contact", delivery_stop.contact,
			["first_name", "last_name", "email_id", "gender"], as_dict=1)

		args.update(delivery_stop.as_dict())
		args.update(contact_info)

		if delivery_stop.delivery_note:
			default_print_format = frappe.get_meta('Delivery Note').default_print_format
			attachments = frappe.attach_print('Delivery Note',
				delivery_stop.delivery_note,
				file_name="Delivery Note",
				print_format=default_print_format or "Standard")

		if not delivery_stop.notified_by_email and contact_info.email_id:
			driver_info = frappe.db.get_value("Driver", driver, ["full_name", "cell_number"], as_dict=1)
			sender_designation = frappe.db.get_value("Employee", sender_email, ["designation"])

			estimated_arrival = cstr(delivery_stop.estimated_arrival)[:-3]
			email_template = frappe.get_doc("Email Template", delivery_notification)
			message = frappe.render_template(email_template.response, args)

			frappe.sendmail(
				recipients=contact_info.email_id,
				sender=sender_email,
				message=message,
				attachments=attachments,
				subject=_(email_template.subject).format(getdate(date).strftime('%d.%m.%y'),
					estimated_arrival))

			frappe.db.set_value("Delivery Stop", delivery_stop.name, "notified_by_email", 1)
			frappe.db.set_value("Delivery Stop", delivery_stop.name,"email_sent_to", contact_info.email_id)
			frappe.msgprint(_("Email sent to {0}").format(contact_info.email_id))
