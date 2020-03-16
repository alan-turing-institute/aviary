
import pytest

import numpy as np

import aviary.scenario.empty_scenario as emps

import aviary.scenario.incremental_ocd_scenario as incs
import aviary.scenario.overflier_climber_scenario as ocs
import aviary.scenario.scenario_generator as sg
import aviary.trajectory.lookup_trajectory_predictor as tp
import aviary.sector.route as sr

from aviary.utils.geo_helper import GeoHelper

@pytest.fixture(scope="function")
def underlying(i_element, cruise_speed_dataframe, climb_time_dataframe, downtrack_distance_dataframe):
    """Test fixture: an overflier-climber scenario to act as the underlying scenario."""

    trajectory_predictor = tp.LookupTrajectoryPredictor(cruise_speed_lookup = cruise_speed_dataframe,
                                                        climb_time_lookup = climb_time_dataframe,
                                                        downtrack_distance_lookup = downtrack_distance_dataframe)

    return ocs.OverflierClimberScenario(sector_element = i_element,
                                        trajectory_predictor = trajectory_predictor,
                                        aircraft_types = ['B744', 'B743'],
                                        callsign_prefixes = ["SPEEDBIRD", "VJ", "DELTA", "EZY"],
                                        flight_levels = [200, 400],
                                        seed = 223)

def test_aircraft_generator_from_empty(i_element):

    target = emps.EmptyScenario(sector_element=i_element)

    for i in range(10):

        ctr = 0
        for x in target.aircraft_generator():
            ctr = ctr + 1

        assert ctr == i

        target = incs.IncrementalOcdScenario(
            underlying_scenario=target,
            seed=i
        )

def test_aircraft_generator(underlying):

    target = incs.IncrementalOcdScenario(
        underlying_scenario=underlying,
        seed = 22,
    )

    # Test across multiple generated scenarios.
    ctr = 0
    for x in target.aircraft_generator():

        assert isinstance(x, dict)
        assert sorted(x.keys()) == [sg.CALLSIGN_KEY, sg.CLEARED_FLIGHT_LEVEL_KEY, sg.CURRENT_FLIGHT_LEVEL_KEY,
                                    sg.DEPARTURE_KEY, sg.DESTINATION_KEY, sg.REQUESTED_FLIGHT_LEVEL_KEY, sg.ROUTE_KEY,
                                    sg.START_POSITION_KEY, sg.AIRCRAFT_TIMEDELTA_KEY, sg.AIRCRAFT_TYPE_KEY]
        # assert isinstance(x[sg.START_POSITION_KEY], tuple)
        # assert not isinstance(x[sg.START_POSITION_KEY][0], tuple)
        # assert x[sg.START_POSITION_KEY][0] == pytest.approx(-0.1275, 10e-8)

        ctr = ctr + 1
        if ctr == 1:
            overflier = x
        if ctr == 2:
            climber = x
        if ctr == 3:
            extra = x

    # Check that the scenario contains precisely three aircraft.
    assert ctr == 3


def test_choose_route_segment(i_element, underlying):

    # Test with five route segments.
    target = incs.IncrementalOcdScenario(
        underlying_scenario=underlying,
        seed = 22,
        start_position_distribution = np.array([1, 0, 0, 0, 0]),
    )

    route = target.route
    fixes = route.fix_points()

    # Test the _pre_fix_index method at the same time.
    assert target._pre_fix_index()[0] == 0

    result = target.choose_route_segment()

    # The first Point in the result should coincide with the fix with index 0.
    assert result[0].x == fixes[0].x
    assert result[0].y == pytest.approx(fixes[0].y, 1e-10)

    # The second Point in the result should be one fifth of the distance along the straight-line route.
    expected_distance = (1/5) * GeoHelper.distance(lat1=fixes[0].y, lon1=fixes[0].x,
                                           lat2=fixes[4].y, lon2=fixes[4].x)
    expected_point = GeoHelper.waypoint_location(lat1=fixes[0].y, lon1=fixes[0].x,
                                                 lat2=fixes[4].y, lon2=fixes[4].x,
                                                 distance_m=expected_distance)
    assert result[1].x == expected_point.x
    assert result[1].y == expected_point.y

    target = incs.IncrementalOcdScenario(
        underlying_scenario=underlying,
        seed = 22,
        start_position_distribution = np.array([0, 1, 0, 0, 0]),
    )

    # Test the _pre_fix_index method at the same time.
    assert target._pre_fix_index()[0] == 1

    result = target.choose_route_segment()

    # The first Point in the result should be one fifth of the distance along the straight-line route.
    expected_distance = (1/5) * GeoHelper.distance(lat1=fixes[0].y, lon1=fixes[0].x,
                                           lat2=fixes[4].y, lon2=fixes[4].x)
    expected_point = GeoHelper.waypoint_location(lat1=fixes[0].y, lon1=fixes[0].x,
                                                 lat2=fixes[4].y, lon2=fixes[4].x,
                                                 distance_m=expected_distance)
    assert result[0].x == expected_point.x
    assert result[0].y == expected_point.y

    # The second Point in the result should be one two fifths of the distance along the straight-line route.
    expected_distance = (2/5) * GeoHelper.distance(lat1=fixes[0].y, lon1=fixes[0].x,
                                           lat2=fixes[4].y, lon2=fixes[4].x)
    expected_point = GeoHelper.waypoint_location(lat1=fixes[0].y, lon1=fixes[0].x,
                                                 lat2=fixes[4].y, lon2=fixes[4].x,
                                                 distance_m=expected_distance)
    assert result[1].x == expected_point.x
    assert result[1].y == pytest.approx(expected_point.y, 1e-10)

    target = incs.IncrementalOcdScenario(
        underlying_scenario=underlying,
        seed = 22,
        start_position_distribution = np.array([0, 0, 0, 0, 1]),
    )

    # Test the _pre_fix_index method at the same time.
    assert target._pre_fix_index()[0] == 2 # Note: this means the central fix is the one before the last fifth segment.

    result = target.choose_route_segment()

    # The first Point in the result should be four fifths of the distance along the straight-line route.
    expected_distance = (4/5) * GeoHelper.distance(lat1=fixes[0].y, lon1=fixes[0].x,
                                           lat2=fixes[4].y, lon2=fixes[4].x)
    expected_point = GeoHelper.waypoint_location(lat1=fixes[0].y, lon1=fixes[0].x,
                                                 lat2=fixes[4].y, lon2=fixes[4].x,
                                                 distance_m=expected_distance)

    assert result[0].x == expected_point.x
    assert result[0].y == pytest.approx(expected_point.y, 1e-10)

    # The second Point in the result should coincide with the fix with index 4 (the end of the route).
    assert result[1].x == fixes[4].x
    assert result[1].y == fixes[4].y

    target = incs.IncrementalOcdScenario(
        underlying_scenario=underlying,
        seed = 22,
        start_position_distribution = np.array([0, 1/2, 0, 1/2, 0]),
    )

    # Test the _pre_fix_index method at the same time.
    assert target._pre_fix_index()[0] == 1 # With this seed, the earlier segment is selected

    result = target.choose_route_segment()

    # The first Point in the result should be one fifth of the distance along the straight-line route.
    expected_distance = (1/5) * GeoHelper.distance(lat1=fixes[0].y, lon1=fixes[0].x,
                                           lat2=fixes[4].y, lon2=fixes[4].x)
    expected_point = GeoHelper.waypoint_location(lat1=fixes[0].y, lon1=fixes[0].x,
                                                 lat2=fixes[4].y, lon2=fixes[4].x,
                                                 distance_m=expected_distance)
    assert result[0].x == expected_point.x
    assert result[0].y == expected_point.y

    # The second Point in the result should be one two fifths of the distance along the straight-line route.
    expected_distance = (2/5) * GeoHelper.distance(lat1=fixes[0].y, lon1=fixes[0].x,
                                           lat2=fixes[4].y, lon2=fixes[4].x)
    expected_point = GeoHelper.waypoint_location(lat1=fixes[0].y, lon1=fixes[0].x,
                                                 lat2=fixes[4].y, lon2=fixes[4].x,
                                                 distance_m=expected_distance)
    assert result[1].x == expected_point.x
    assert result[1].y == pytest.approx(expected_point.y, 1e-10)

    target = incs.IncrementalOcdScenario(
        underlying_scenario=underlying,
        seed = 28,
        start_position_distribution = np.array([0, 1/2, 0, 1/2, 0]),
    )

    # Test the _pre_fix_index method at the same time.
    # With the different seed, the route is the same but the later segment is selected:
    assert target.route.fix_names() == route.fix_names()
    assert target._pre_fix_index()[0] == 2

    result = target.choose_route_segment()

    # The first Point in the result should be three fifths of the distance along the straight-line route.
    expected_distance = (3/5) * GeoHelper.distance(lat1=fixes[0].y, lon1=fixes[0].x,
                                           lat2=fixes[4].y, lon2=fixes[4].x)
    expected_point = GeoHelper.waypoint_location(lat1=fixes[0].y, lon1=fixes[0].x,
                                                 lat2=fixes[4].y, lon2=fixes[4].x,
                                                 distance_m=expected_distance)

    assert result[0].x == expected_point.x
    assert result[0].y == pytest.approx(expected_point.y, 1e-10)

    # The second Point in the result should be four fifths of the distance along the straight-line route.
    expected_distance = (4/5) * GeoHelper.distance(lat1=fixes[0].y, lon1=fixes[0].x,
                                           lat2=fixes[4].y, lon2=fixes[4].x)
    expected_point = GeoHelper.waypoint_location(lat1=fixes[0].y, lon1=fixes[0].x,
                                                 lat2=fixes[4].y, lon2=fixes[4].x,
                                                 distance_m=expected_distance)

    assert result[1].x == expected_point.x
    assert result[1].y == pytest.approx(expected_point.y, 1e-10)


