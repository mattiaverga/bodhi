# Copyright © 2019 Red Hat, Inc.
#
# This file is part of Bodhi.
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
"""Test the bodhi.server.consumers package."""
from unittest import mock

from fedora_messaging.api import Message
from fedora_messaging.exceptions import Nack

from bodhi.server import config
from bodhi.server.consumers import composer, Consumer, signed, updates
from bodhi.tests.server import base


@mock.patch.dict(
    config.config,
    {'pungi.cmd': '/usr/bin/true', 'compose_dir': '/usr/bin/true',
     'compose_stage_dir': '/usr/bin/true'})
class TestConsumer(base.BaseTestCase):
    """Test class for the Consumer class."""

    @mock.patch('bodhi.server.consumers.bugs.set_bugtracker')
    @mock.patch('bodhi.server.consumers.buildsys.setup_buildsystem')
    @mock.patch('bodhi.server.consumers.initialize_db')
    @mock.patch('bodhi.server.consumers.log.info')
    def test__init___with_composer(self, info, initialize_db, setup_buildsystem, set_bugtracker):
        """Test the __init__() method when the composer is installed."""
        consumer = Consumer()

        self.assertTrue(isinstance(consumer.composer_handler, composer.ComposerHandler))
        self.assertTrue(isinstance(consumer.signed_handler, signed.SignedHandler))
        self.assertTrue(isinstance(consumer.updates_handler, updates.UpdatesHandler))
        info.assert_called_once_with('Initializing Bodhi')
        initialize_db.assert_called_once_with(config.config)
        setup_buildsystem.assert_called_once_with(config.config)
        set_bugtracker.assert_called_once_with()

    @mock.patch('bodhi.server.consumers.bugs.set_bugtracker')
    @mock.patch('bodhi.server.consumers.buildsys.setup_buildsystem')
    @mock.patch('bodhi.server.consumers.ComposerHandler', None)
    @mock.patch('bodhi.server.consumers.initialize_db')
    @mock.patch('bodhi.server.consumers.log.info')
    def test__init___without_composer(self, info, initialize_db, setup_buildsystem, set_bugtracker):
        """Test the __init__() method when the composer is not installed."""
        consumer = Consumer()

        self.assertIsNone(consumer.composer_handler)
        self.assertTrue(isinstance(consumer.signed_handler, signed.SignedHandler))
        self.assertTrue(isinstance(consumer.updates_handler, updates.UpdatesHandler))
        self.assertEqual(
            info.mock_calls,
            [mock.call('Initializing Bodhi'),
             mock.call('The composer is not installed - Bodhi will ignore composer.start '
                       'messages.')])
        initialize_db.assert_called_once_with(config.config)
        setup_buildsystem.assert_called_once_with(config.config)
        set_bugtracker.assert_called_once_with()

    @mock.patch('bodhi.server.consumers.ComposerHandler')
    def test_messaging_callback_composer_installed(self, Handler):
        """Test receiving a composer.start message when the composer is installed."""
        msg = Message(
            topic="org.fedoraproject.prod.bodhi.composer.start",
            body={}
        )
        handler = mock.Mock()
        Handler.side_effect = lambda: handler

        Consumer()(msg)

        handler.assert_called_once_with(msg)

    @mock.patch('bodhi.server.consumers.ComposerHandler', None)
    @mock.patch('bodhi.server.consumers.log.exception')
    def test_messaging_callback_composer_not_installed(self, error):
        """Test receiving a composer.start message when the composer is not installed."""
        msg = Message(
            topic="org.fedoraproject.prod.bodhi.composer.start",
            body={}
        )

        with self.assertRaises(Nack) as exc:
            Consumer()(msg)

        msg = ('Unable to process composer.start message topics because the Composer is not '
               f'installed: Unable to handle message: {msg}')
        error.assert_called_once_with(msg)
        self.assertEqual(str(exc.exception), msg)

    @mock.patch('bodhi.server.consumers.AutomaticUpdateHandler')
    @mock.patch('bodhi.server.consumers.SignedHandler')
    def test_messaging_callback_signed_automatic_update(self,
                                                        SignedHandler,
                                                        AutomaticUpdateHandler):
        msg = Message(
            topic="org.fedoraproject.prod.buildsys.tag",
            body={}
        )

        signed_handler = mock.Mock()
        SignedHandler.side_effect = lambda: signed_handler

        automatic_update_handler = mock.Mock()
        AutomaticUpdateHandler.side_effect = lambda: automatic_update_handler

        Consumer()(msg)

        signed_handler.assert_called_once_with(msg)
        automatic_update_handler.assert_called_once_with(msg)

    @mock.patch('bodhi.server.consumers.UpdatesHandler')
    def test_messaging_callback_updates_testing(self, Handler):
        msg = Message(
            topic="org.fedoraproject.prod.bodhi.update.request.testing",
            body={}
        )
        handler = mock.Mock()
        Handler.side_effect = lambda: handler

        Consumer()(msg)

        handler.assert_called_once_with(msg)

    @mock.patch('bodhi.server.consumers.UpdatesHandler')
    def test_messaging_callback_updates_edit(self, Handler):
        msg = Message(
            topic="org.fedoraproject.prod.bodhi.update.edit",
            body={}
        )
        handler = mock.Mock()
        Handler.side_effect = lambda: handler

        Consumer()(msg)

        handler.assert_called_once_with(msg)

    @mock.patch('bodhi.server.consumers.GreenwaveHandler')
    def test_messaging_callback_greenwave(self, Handler):
        msg = Message(
            topic="org.fedoraproject.prod.greenwave.decision.update",
            body={}
        )
        handler = mock.Mock()
        Handler.side_effect = lambda: handler
        Consumer()(msg)
        handler.assert_called_once_with(msg)
