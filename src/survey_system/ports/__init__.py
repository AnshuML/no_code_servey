"""Ports (protocols): swap implementations without changing core survey logic."""

from survey_system.ports.channels import OutboundChannel
from survey_system.ports.persistence import ResponsePersistence
from survey_system.ports.speech import SpeechToText

__all__ = ["OutboundChannel", "ResponsePersistence", "SpeechToText"]
