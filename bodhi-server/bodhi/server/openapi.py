# Copyright © 2007-2019 Red Hat, Inc. and others.
#
# This file is part of Bodhi.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""Integration with pyramid_openapi3."""

from datetime import datetime
from zope.interface import providedBy
import logging as python_logging
import os

from pyramid.config import Configurator
from pyramid.interfaces import IJSONAdapter
from pyramid.renderers import JSON, _marker
from pyramid.request import Request
import typing as t

log = python_logging.getLogger(__name__)


class JSON_v2(JSON):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _make_default(self, request):
        """Overrides the default JSON method to make use of __json_v2__()."""
        def default(obj):
            if hasattr(obj, '__json_v2__'):
                return obj.__json_v2__(request)
            elif hasattr(obj, '__json__'):
                return obj.__json__(request)
            obj_iface = providedBy(obj)
            adapters = self.components.adapters
            result = adapters.lookup(
                (obj_iface,), IJSONAdapter, default=_marker
            )
            if result is _marker:
                raise TypeError('%r is not JSON serializable' % (obj,))
            return result(obj, request)

        return default


def includeme(config: Configurator) -> None:
    """Configure support for serving and handling OpenAPI requests."""

    config.include("pyramid_openapi3")
    config.pyramid_openapi3_spec_directory(
        os.path.join(os.path.dirname(__file__), 'openapi.yaml'),
        route='/api/v2/spec')
    config.pyramid_openapi3_add_explorer(route='/api/v2/')

    config.add_renderer("json_v2", json_v2_renderer())

    # Routes
    #config.add_route("api_v2_overrides", "/api/v2/overrides/")


def json_v2_renderer() -> JSON:
    """Configure a JSON renderer that supports rendering datetimes."""
    renderer = JSON_v2()
    renderer.add_adapter(datetime, datetime_adapter)
    return renderer


def datetime_adapter(obj: datetime, request: Request) -> str:
    """OpenAPI spec defines date-time notation as RFC 3339, section 5.6.  # noqa

    For example: 2017-07-21T17:32:28.001Z

    The `timespec="milliseconds"` is required because the frontend expects
    the format to be exactly `HH:MM:SS.sss` and not `HH:MM:SS` or
    `HH:MM:SS.ssssss` which Python would decide automatically.
    """
    return obj.isoformat(timespec="milliseconds") + "Z"
