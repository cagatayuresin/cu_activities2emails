# -*- coding: utf-8 -*-
# Cagatay URESIN <cagatayuresin@gmail.com>


import smtplib
import logging
import pip
import uuid
import re
import datetime as dt


try:
    import pytz
except ImportError:
    pip.main(["install", "pytz"])
    import pytz

try:
    import icalendar
except ImportError:
    pip.main(["install", "icalendar"])
    import icalendar

from email import encoders
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart

from odoo import models, fields, api


_logger = logging.getLogger(__name__)


class CuActivities2EmailsEvent(models.Model):
    _description = "Activities 2 Emails Equalizer Event"
    _inherit = ["calendar.event"]

    is_new = fields.Boolean("Is it synchronized", default=True)
    email_invite_id = fields.Char()

    @api.onchange("name", "description", "start", "stop")
    def _onchange_anything(self):
        self.is_new = True


class CuActivities2EmailsActivity(models.Model):
    _description = "Activities 2 Emails Equalizer Activity"
    _inherit = ["mail.activity"]

    is_new = fields.Boolean("Is it synchronized", default=True)
    email_invite_id = fields.Char()

    def get_smtp_server(self):
        try:
            smtp_server = self.env["ir.mail_server"].sudo().search([("active", "=", True)], order="sequence")
            return {
                "host": smtp_server.smtp_host,
                "port": smtp_server.smtp_port,
                "user": smtp_server.smtp_user,
                "pass": smtp_server.smtp_pass,
                "from": smtp_server.from_filter,
            }
        except Exception as err:
            _logger.exception(f"[CU_Activities2Emails] Unexpected {err}, {type(err)}")
            return False

    def get_new_activities(self):
        return self.env["mail.activity"].sudo().search([("is_new", "=", True)])

    def get_new_calendar_events(self):
        return self.env["calendar.event"].sudo().search([("is_new", "=", True)])

    @staticmethod
    def activity_parser(activity):
        calendar_event_id = activity.calendar_event_id or False
        if not calendar_event_id:
            return {
                "dtstart": activity.date_deadline,
                "dtend": activity.date_deadline,
                "description": activity.note or "No Description",
                "summary": activity.summary or "No Summary",
                "type": activity.activity_type_id.name or "No Type",
                # "attended": [activity.user_id.login],
                "attended": ["cagatayuresin@gmail.com"],
            }
        return {
            "dtstart": activity.calendar_event_id.start,
            "dtend": activity.calendar_event_id.stop,
            "description": activity.calendar_event_id.description or "No Description",
            "summary": activity.calendar_event_id.name or "No Summary",
            "type": activity.activity_type_id.name or "No Type",
            # "attended": [
            #     attendee.partner_id.email
            #     for attendee in self.env["calendar.attendee"]
            #     .sudo()
            #     .search([("event_id", "=", activity.calendar_event_id.id)])
            # ],
            "attended": ["cagatayuresin@gmail.com"],
        }

    @staticmethod
    def event_parser(event):
        return {
            "dtstart": event.start,
            "dtend": event.stop,
            "description": event.description or "No Description",
            "summary": event.name or "No Summary",
            "type": "Event",
            # "attended": [
            #     attendee.partner_id.email
            #     for attendee in self.env["calendar.attendee"].sudo().search([("event_id", "=", event.id)])
            # ],
            "attended": ["cagatayuresin@gmail.com"],
        }

    @staticmethod
    def date_corrector(date_or_time):
        if type(date_or_time) == dt.date:
            return dt.datetime.combine(date_or_time, dt.time(0, 0, 0))
        elif type(date_or_time) == dt.datetime:
            return date_or_time
        else:
            return False

    @staticmethod
    def html_sanitizer(the_string):
        return re.sub("\\s+", " ", re.sub('</?[\\w="\\-\\s]*>', " ", the_string)).strip()

    def sending(self, activity):
        smtp_server = self.get_smtp_server()
        if not smtp_server:
            return False
        calendar = icalendar.Calendar()
        calendar.add("prodid", "-//Cagatay URESIN//CU Activities 2 Emails for Odoo//TR")
        calendar.add("version", "2.0")
        calendar.add("method", "REQUEST")
        event = icalendar.Event()
        event.add("attendee", activity["attended"])
        event.add("organizer", smtp_server["from"])
        event.add("status", "confirmed")
        event.add("category", "Event")
        event.add("summary", f"""{activity["type"]} - {activity["summary"]}""")
        event.add(
            "description",
            f"""{activity["type"]} - {activity["summary"]} - {self.html_sanitizer(activity["description"])}""",
        )
        event.add("location", "ODOO")
        tz = pytz.timezone("UTC")
        event.add("dtstart", tz.localize(self.date_corrector(activity["dtstart"])))
        event.add("dtstamp", dt.datetime.now())
        event["uid"] = int(uuid.uuid1())
        event.add("priority", 5)
        event.add("sequence", 1)
        event.add("created", tz.localize(dt.datetime.now()))
        if type(activity["dtstart"]) == dt.datetime:
            event.add("dtend", tz.localize(self.date_corrector(activity["dtend"])))
            alarm = icalendar.Alarm()
            alarm.add("action", "DISPLAY")
            alarm.add("description", "Reminder")
            alarm.add("TRIGGER;RELATED=START", "-PT{0}H".format(1))
            event.add_component(alarm)
        else:
            event.add("dtend", tz.localize(self.date_corrector(activity["dtend"]) + dt.timedelta(days=1)))
            event.allday = True
        calendar.add_component(event)
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"""{activity["type"]} - {activity["summary"]}"""
        msg["From"] = smtp_server["from"]
        msg["Content-class"] = "urn:content-classes:calendarmessage"
        msg.attach(MIMEText(f"""{activity["type"]} - {activity["summary"]} - {activity["description"]}"""))
        filename = "invite.ics"
        part = MIMEBase("text", "calendar", method="REQUEST", name=filename)
        part.set_payload(calendar.to_ical())
        encoders.encode_base64(part)
        part.add_header("Content-Description", filename)
        part.add_header("Content-class", "urn:content-classes:calendarmessage")
        part.add_header("Filename", filename)
        part.add_header("Path", filename)
        msg.attach(part)
        s = smtplib.SMTP(smtp_server["host"], int(smtp_server["port"]))
        s.starttls()
        s.login(smtp_server["user"], smtp_server["pass"])
        for to_mail in activity["attended"]:
            msg["To"] = to_mail
            s.sendmail(msg["From"], [msg["To"]], msg.as_string())
        s.quit()

    def sync(self):
        activities = self.get_new_activities()
        for activity in activities:
            parsed_activity = self.activity_parser(activity)
            try:
                self.sending(parsed_activity)
                _logger.info(f"[CU_Activities2Emails] {parsed_activity} sent.")
                activity.is_new = False
            except Exception as err:
                _logger.exception(f"[CU_Activities2Emails] Unexpected {type(err)}")
        events = self.get_new_calendar_events()
        for event in events:
            parsed_events = self.event_parser(event)
            try:
                self.sending(parsed_events)
                _logger.info(f"[CU_Activities2Emails] {parsed_events} sent.")
                event.is_new = False
            except Exception as err:
                _logger.exception(f"[CU_Activities2Emails] Unexpected {type(err)}")

    @api.onchange("user_id", "acivity_type_id", "summary", "note", "date_deadline")
    def _onchange_anything(self):
        self.is_new = True
