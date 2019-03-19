"""Tests for the heos class."""
import asyncio

import pytest

from pyheos import const
from pyheos.dispatch import Dispatcher
from pyheos.heos import Heos

from . import get_fixture


def test_init():
    """Test init sets properties."""
    heos = Heos('127.0.0.1')
    assert isinstance(heos.dispatcher, Dispatcher)
    assert not heos.players
    assert heos.get_player(1) is None


@pytest.mark.asyncio
async def test_connect_loads_players_and_subscribes(mock_device, heos):
    """Test the heos connect method."""
    # Assert 1st connection is used for commands
    assert len(mock_device.connections) == 2
    command_log = mock_device.connections[0]
    assert not command_log.is_registered_for_events

    # Assert 2nd connection is registered for events
    event_log = mock_device.connections[1]
    assert event_log.is_registered_for_events

    # Assert players loaded
    assert len(heos.players) == 2
    player = heos.get_player(1)
    assert player.player_id == 1
    assert player.name == 'Back Patio'
    assert player.ip_address == '192.168.0.1'
    assert player.line_out == 1
    assert player.model == 'HEOS Drive'
    assert player.network == 'wired'
    assert player.state == const.PLAY_STATE_STOP
    assert player.version == '1.493.180'
    assert player.volume == 36
    assert not player.is_muted
    assert player.repeat == const.REPEAT_OFF
    assert not player.shuffle


@pytest.mark.asyncio
async def test_player_state_changed_event(mock_device, heos):
    """Test playing state updates when event is received."""
    # assert not playing
    player = heos.get_player(1)
    assert player.state == const.PLAY_STATE_STOP

    # Attach dispatch handler
    signal = asyncio.Event()

    async def handler(player_id: int, event: str):
        assert player_id == player.player_id
        assert event == const.EVENT_PLAYER_STATE_CHANGED
        signal.set()
    heos.dispatcher.connect(const.SIGNAL_PLAYER_UPDATED, handler)

    # Write event through mock device
    event_to_raise = (await get_fixture("event.player_state_changed")) \
        .replace("{player_id}", str(player.player_id)) \
        .replace("{state}", const.PLAY_STATE_PLAY)
    await mock_device.write_event(event_to_raise)

    # Wait until the signal is set or timeout
    await asyncio.wait_for(signal.wait(), 1)
    # Assert state changed
    assert player.state == const.PLAY_STATE_PLAY
    assert heos.get_player(2).state == const.PLAY_STATE_STOP


@pytest.mark.asyncio
async def test_player_now_playing_changed_event(mock_device, heos):
    """Test now playing updates when event is received."""
    # assert current state
    player = heos.get_player(1)
    now_playing = player.now_playing_media
    assert now_playing.album == ''
    assert now_playing.type == 'song'
    assert now_playing.album_id == ''
    assert now_playing.artist == ''
    assert now_playing.image_url == ''
    assert now_playing.media_id == 'catalog/playlists/genres'
    assert now_playing.queue_id == 1
    assert now_playing.song_id == 13
    assert now_playing.song == 'Disney Hits'
    assert now_playing.station is None

    # Attach dispatch handler
    signal = asyncio.Event()

    async def handler(player_id: int, event: str):
        assert player_id == player.player_id
        assert event == const.EVENT_PLAYER_NOW_PLAYING_CHANGED
        signal.set()
    heos.dispatcher.connect(const.SIGNAL_PLAYER_UPDATED, handler)

    # Write event through mock device
    mock_device.register_one_time(
        "player/get_now_playing_media",
        "player.get_now_playing_media_changed")
    event_to_raise = (await get_fixture("event.player_now_playing_changed")) \
        .replace("{player_id}", str(player.player_id))
    await mock_device.write_event(event_to_raise)

    # Wait until the signal is set or timeout
    await asyncio.wait_for(signal.wait(), 1)
    # Assert state changed
    assert now_playing.album == "I've Been Waiting (Single) (Explicit)"
    assert now_playing.type == 'station'
    assert now_playing.album_id == '1'
    assert now_playing.artist == 'Lil Peep & ILoveMakonnen'
    assert now_playing.image_url == 'http://media/url'
    assert now_playing.media_id == '2PxuY99Qty'
    assert now_playing.queue_id == 1
    assert now_playing.song_id == 1
    assert now_playing.song == "I've Been Waiting (feat. Fall Out Boy)"
    assert now_playing.station == "Today's Hits Radio"


@pytest.mark.asyncio
async def test_player_volume_changed_event(mock_device, heos):
    """Test volume state updates when event is received."""
    # assert not playing
    player = heos.get_player(1)
    assert player.volume == 36
    assert not player.is_muted

    # Attach dispatch handler
    signal = asyncio.Event()

    async def handler(player_id: int, event: str):
        assert player_id == player.player_id
        assert event == const.EVENT_PLAYER_VOLUME_CHANGED
        signal.set()
    heos.dispatcher.connect(const.SIGNAL_PLAYER_UPDATED, handler)

    # Write event through mock device
    event_to_raise = (await get_fixture("event.player_volume_changed")) \
        .replace("{player_id}", str(player.player_id)) \
        .replace("{level}", '50') \
        .replace("{mute}", 'on')
    await mock_device.write_event(event_to_raise)

    # Wait until the signal is set or timeout
    await asyncio.wait_for(signal.wait(), 1)
    # Assert state changed
    assert player.volume == 50
    assert player.is_muted
    assert heos.get_player(2).volume == 36
    assert not heos.get_player(2).is_muted


@pytest.mark.asyncio
async def test_player_now_playing_progress_event(mock_device, heos):
    """Test now playing progress updates when event received."""
    # assert not playing
    player = heos.get_player(1)
    assert player.now_playing_media.duration is None
    assert player.now_playing_media.current_position is None

    # Attach dispatch handler
    signal = asyncio.Event()

    async def handler(player_id: int, event: str):
        assert player_id == player.player_id
        assert event == const.EVENT_PLAYER_NOW_PLAYING_PROGRESS
        signal.set()
    heos.dispatcher.connect(const.SIGNAL_PLAYER_UPDATED, handler)

    # Write event through mock device
    event_to_raise = (await get_fixture("event.player_now_playing_progress")) \
        .replace("{player_id}", str(player.player_id)) \
        .replace("{cur_pos}", '113000') \
        .replace("{duration}", '210000')
    await mock_device.write_event(event_to_raise)

    # Wait until the signal is set or timeout
    await asyncio.wait_for(signal.wait(), 1)
    # Assert state changed
    assert player.now_playing_media.duration == 210000
    assert player.now_playing_media.current_position == 113000
    assert heos.get_player(2).now_playing_media.duration is None
    assert heos.get_player(2).now_playing_media.current_position is None


@pytest.mark.asyncio
async def test_repeat_mode_changed_event(mock_device, heos):
    """Test repeat mode changes when event received."""
    # assert not playing
    player = heos.get_player(1)
    assert player.repeat == const.REPEAT_OFF

    # Attach dispatch handler
    signal = asyncio.Event()

    async def handler(player_id: int, event: str):
        assert player_id == player.player_id
        assert event == const.EVENT_REPEAT_MODE_CHANGED
        signal.set()
    heos.dispatcher.connect(const.SIGNAL_PLAYER_UPDATED, handler)

    # Write event through mock device
    event_to_raise = await get_fixture("event.repeat_mode_changed")
    await mock_device.write_event(event_to_raise)

    # Wait until the signal is set or timeout
    await asyncio.wait_for(signal.wait(), 1)
    # Assert state changed
    assert player.repeat == const.REPEAT_ON_ALL


@pytest.mark.asyncio
async def test_shuffle_mode_changed_event(mock_device, heos):
    """Test shuffle mode changes when event received."""
    # assert not playing
    player = heos.get_player(1)
    assert not player.shuffle

    # Attach dispatch handler
    signal = asyncio.Event()

    async def handler(player_id: int, event: str):
        assert player_id == player.player_id
        assert event == const.EVENT_SHUFFLE_MODE_CHANGED
        signal.set()
    heos.dispatcher.connect(const.SIGNAL_PLAYER_UPDATED, handler)

    # Write event through mock device
    event_to_raise = await get_fixture("event.shuffle_mode_changed")
    await mock_device.write_event(event_to_raise)

    # Wait until the signal is set or timeout
    await asyncio.wait_for(signal.wait(), 1)
    # Assert state changed
    assert player.shuffle
