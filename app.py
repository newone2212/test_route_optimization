import requests
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import webbrowser
import time
import osmnx as ox
import networkx as nx
import taxicab as tc
import pyttsx3

BING_MAPS_API_KEY = 'Amp0yQEv00Vz2-auovohQoncrJxr6bDzul0mpw6_WCzq9aMrL5DygIUryfW7NxwE'
def geocode_address(address):
    url = f'https://dev.virtualearth.net/REST/v1/Locations?query={address}&key={BING_MAPS_API_KEY}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        if 'resourceSets' in data and len(data['resourceSets']) > 0:
            resources = data['resourceSets'][0]['resources']
            if len(resources) > 0:
                point = resources[0]['point']
                latitude = point['coordinates'][0]
                longitude = point['coordinates'][1]
                return f'{latitude},{longitude}'
    return None

def create_data_model(locations):
    distance_matrix = []
    time_matrix=[]
    for i in range(len(locations)):
        distance_row = []
        time_row=[]
        for j in range(len(locations)):
            if i == j:
                distance_row.append(0)
            else:
                coords_1 = locations[i]['coordinates']
                coords_2 = locations[j]['coordinates']
                distance = get_distance(coords_1, coords_2)
                # time_duration=get_time(coords_1, coords_2)
                # print(time_duration)
                distance_row.append(distance)
                # time_row.append(time_duration)
        distance_matrix.append(distance_row)
        # time_matrix.append(time_duration)

    data = {
        'distance_matrix': distance_matrix,
        'num_vehicles': 1,
        # 'time_matrix':time_matrix,
        'depot': 0
    }

    return data

# def get_direction()

def get_distance(coords_1, coords_2):
    url = f'https://dev.virtualearth.net/REST/v1/Routes/DistanceMatrix?origins={coords_1}&destinations={coords_2}&travelMode=driving&key={BING_MAPS_API_KEY}'
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        print(data['resourceSets'])
        if 'resourceSets' in data and len(data['resourceSets']) > 0:
            resources = data['resourceSets'][0]['resources']
            if len(resources) > 0:
                return resources[0]['results'][0]['travelDistance']
            
    return float('inf')

# def get_time(coords_1, coords_2):
#     url = f'https://dev.virtualearth.net/REST/v1/Routes/DistanceMatrix?origins={coords_1}&destinations={coords_2}&travelMode=driving&key={BING_MAPS_API_KEY}'
#     response = requests.get(url)
#     if response.status_code == 200:
#         data = response.json()
#         print(data['resourceSets'])
#         if 'resourceSets' in data and len(data['resourceSets']) > 0:
#             resources = data['resourceSets'][0]['resources']
#             if len(resources) > 0:
#                 print(resources[0]['results'][0]['travelDuration'])
#                 return resources[0]['results'][0]['travelDuration']
            
#     return float('inf')

def solve_tsp(data):
    manager = pywrapcp.RoutingIndexManager(len(data['distance_matrix']),
                                           data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)


    def distance_callback(from_index, to_index):
        return data['distance_matrix'][manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    dimension_name = 'Distance'
    routing.AddDimension(
        transit_callback_index,
        0,
        10000,
        True,
        dimension_name)

    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)

    solution = routing.SolveWithParameters(search_parameters)
    print(solution)
    if solution:
        return solution, routing, manager
    else:
        print('No solution found!')
        return None

def print_solution(solution, routing, manager, data, locations):
    total_distance = 0
    index = routing.Start(0)
    plan_output = 'Route for Vehicle 0:\n'
    route_distance = 0
    while not routing.IsEnd(index):
        node_index = manager.IndexToNode(index)
        plan_output += f'{locations[node_index]["name"]} -> '
        next_node_index = manager.IndexToNode(solution.Value(routing.NextVar(index)))
        route_distance += data['distance_matrix'][node_index][next_node_index]
        index = solution.Value(routing.NextVar(index))

    plan_output += f'{locations[manager.IndexToNode(index)]["name"]}'
    route_distance += data['distance_matrix'][manager.IndexToNode(index)][0]
    plan_output += f' (Distance: {route_distance:.2f} miles)\n'
    total_distance += route_distance

    print(plan_output)
    print('Total distance:', total_distance, 'miles')
    map_url = generate_map_url(locations, solution, routing, manager, data)
    print('Map URL:', map_url)

    return plan_output, total_distance, map_url

def generate_map_url(locations, solution, routing, manager, data):
    indices = [manager.IndexToNode(solution.Value(routing.NextVar(i))) for i in range(routing.Size())]
    waypoints = '~'.join([f'{locations[index]["coordinates"]}' for index in indices])
    map_url = f'https://www.bing.com/maps?rtp={locations[indices[0]]["coordinates"]}~{waypoints}&mode=route'
    return map_url

def open_map(map_url):
    #webbrowser.open(map_url, new=2)
    webbrowser.open_new_tab(map_url)

def speak(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)  # You can adjust the speech rate here
    engine.say(text)
    engine.runAndWait()

def main():
    locations = []
    num_locations = int(input('Enter the number of  patients locations: '))
    for i in range(num_locations):
        address = input(f'Enter the address of patients {i+1}: ')
        coordinates = geocode_address(address)
        if coordinates:
            locations.append({'name': f'Location {i+1}', 'address': address, 'coordinates': coordinates})
            # print(locations)
        else:
            print(f'Failed to geocode address: {address}')

    data = create_data_model(locations)
    print(data)

    solution, routing, manager = solve_tsp(data)

    if solution:
        plan_output, total_distance, map_url = print_solution(solution, routing, manager, data, locations)
        # open_map(map_url)
        time.sleep(5)  # Adjust this delay to wait for the map to load

        # speak(f'Total distance: {total_distance:.2f} miles')
        # speak(plan_output)
        # speak('In this map you can enter the location and get shortest possible path highlighted for your convenience')
    else:
        print('No solution found!')

if __name__ == '__main__':
    main()