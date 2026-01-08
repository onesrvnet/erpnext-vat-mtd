# -*- coding: utf-8 -*-
# Copyright (c) 2021 Software to Hardware Ltd. and contributors
# For license information, please see license.txt

import platform
import hashlib
import frappe
import urllib.parse
from datetime import datetime, timezone
import uuid
import json
from urllib.parse import quote

DEVICE_ID_COOKIE = "Gov-Client-Device-ID"

def get_fraud_prevention_headers():

    utc_now = datetime.now(timezone.utc).isoformat()[0:23] + "Z"

    h = {}
    h["Gov-Client-Connection-Method"] = "WEB_APP_VIA_SERVER"
    # Deprecated -> not mentioned in API docs
    #h["Gov-Client-Browser-Do-Not-Track"] = str(
    #    bool(frappe.request.headers.get("DNT"))).lower()
    # We don't issue software licences.
    # It is true that no one issues licenses, but HMRC requires this header.
    # The only exception where this header cannot be sent according to hmrc is " If you are unable to submit a header, you must contact us to explain why. Make sure you include full details of the restrictions."
    # We will use the installation GUID as a replacement of a license key as it should be just as immutable -> you should consult HMRC
    guid = frappe.db.get_single_value("HMRC API Settings", "installation_guid")
    h["Gov-Vendor-License-IDs"] = "{}={}".format(
        "ERPNext", hashlib.sha256(guid.encode("utf-8")).hexdigest())
    h["Gov-Vendor-Product-Name"] = "ERPNext-MTD-VAT-Module"
    h["Gov-Vendor-Version"] = "erpnext-mtd-module=1.0&{}={}".format(
        platform.system(), platform.release()
    )

    # Get or generate and store client device ID
    client_device_id = frappe.request.cookies.get(DEVICE_ID_COOKIE)
    if not client_device_id:
        client_device_id = str(uuid.uuid4())
        frappe.local.cookie_manager.set_cookie(DEVICE_ID_COOKIE,
            client_device_id)
    h["Gov-Client-Device-ID"] = client_device_id

    # Headers from this application
    h["Gov-Client-User-IDs"] = "frappe={}".format(
        urllib.parse.quote(frappe.session.user))

    # Headers from client javascript
    chdr = json.loads(frappe.request.form["fraud_prevention"])
    h["Gov-Client-Browser-JS-User-Agent"] = chdr.get("UA")
    tzoffset_minutes = chdr.get("TimezoneOffsetMinutes")
    if tzoffset_minutes is not None:
        tzoffset_minutes = int(tzoffset_minutes)
        h["Gov-Client-Timezone"] = "UTC{}{:02d}:{:02d}".format(
            "-" if tzoffset_minutes >= 0 else "+", # Direction is ok
            abs(tzoffset_minutes) // 60,
            abs(tzoffset_minutes) % 60
        )
    h["Gov-Client-Window-Size"] = "width={}&height={}".format(
        chdr["WindowWidth"], chdr["WindowHeight"]
    )
    h["Gov-Client-Screens"] = "width={}&height={}&scaling-factor={}&colour-depth={}".format(
        chdr["ScreenWidth"], chdr["ScreenHeight"], chdr["ScreenScalingFactor"],
        chdr["ScreenColorDepth"]
    )

    # Traefik headers
    # Parse all required gov headers via reverse proxy vars
    h["Gov-Client-Public-IP"] = get_client_public_ip()
    h["Gov-Client-Public-IP-Timestamp"] = utc_now
    ip = frappe.db.get_single_value("HMRC API Settings", "public_ip")
    if ip is not None:
        h["Gov-Vendor-Public-IP"] = ip

    h["Gov-Vendor-Forwarded"] = f"by={encode_ip(ip)}&for={encode_ip(get_client_public_ip())}"


    # Client headers - only replace non specified headers
    # In production this should come from your proxy front end
    if frappe.db.get_single_value("HMRC API Settings", "gov_ip_headers"):
        for hdr in ("Gov-Client-Public-IP", "Gov-Client-Public-IP-Timestamp",
                    "Gov-Client-Public-Port", "Gov-Vendor-Public-IP",
                    "Gov-Vendor-Forwarded"):
            if hdr not in h:
                h[hdr] = frappe.get_request_header(hdr)
    # Header not required for WEB_APP_VIA_SERVER connection method.
    #h["Gov-Client-Browser-Plugins"] = chdr["Plugins"]

    # Suggested method does not work. If GOV wants these then GOV can tell us
    # how they want us to get them.
    
    # Headers below are not required for WEB_APP_VIA_SERVER connection method.
    # Commenting out
    #h["Gov-Client-Local-IPs"] = ""
    #h["Gov-Client-Local-IPs-Timestamp"] = ""

    # We don't use multi-factor.
    #h["Gov-Client-Multi-Factor"] = ""

    return h

@frappe.whitelist()
def http_header_feedback():
    return frappe.request.headers

# Identify public IP from reverse-proxy
def get_client_public_ip():
    req = frappe.local.request
    xff = req.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return req.headers.get("X-Real-Ip") or req.remote_addr

def encode_ip(ip):
    # IPv4 unaffected; IPv6 must be percent-encoded
    return quote(ip, safe="")

