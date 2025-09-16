import csv
from ortools.constraint_solver import pywrapcp, routing_enums_pb2

SPEED_KMPH = 90
VISIT_TIME_MIN = 120
WORK_START = 8 * 60
WORK_END = 17 * 60
MAX_WORK_MIN = WORK_END - WORK_START  # 540 minutes

def read_matrix(filename):
    with open(filename, 'r', encoding='utf-8-sig') as f:
        reader = list(csv.reader(f))
        headers = reader[0][1:]  # Exclude first empty cell
        matrix = [list(map(float, row[1:])) for row in reader[1:]]
        return matrix, headers

def create_model(matrix, headers):
    size = len(matrix)
    time_matrix = [[int((matrix[i][j] / SPEED_KMPH) * 60) for j in range(size)] for i in range(size)]
    est_stops_per_day = max(1, MAX_WORK_MIN // (VISIT_TIME_MIN + 30))
    num_days = (size - 1 + est_stops_per_day - 1) // est_stops_per_day

    return {
        'time_matrix': time_matrix,
        'num_vehicles': num_days,
        'depot': 0,
        'headers': headers,
        'visit_duration': VISIT_TIME_MIN,
        'time_windows': [(0, MAX_WORK_MIN)] * size  # timetable 0–540 minutes
    }

def solve_schedule(data):
    manager = pywrapcp.RoutingIndexManager(len(data['time_matrix']), data['num_vehicles'], data['depot'])
    routing = pywrapcp.RoutingModel(manager)

    def time_callback(from_idx, to_idx):
        from_node = manager.IndexToNode(from_idx)
        to_node = manager.IndexToNode(to_idx)

        service = data['visit_duration'] if from_node != data['depot'] else 0
        travel = data['time_matrix'][from_node][to_node]
        return service + travel


    callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(callback_index)

    routing.AddDimension(callback_index, 60, MAX_WORK_MIN, False, 'Time')
    time_dim = routing.GetDimensionOrDie('Time')

    # Restriction for nodes
    for i, window in enumerate(data['time_windows']):
        idx = manager.NodeToIndex(i)
        time_dim.CumulVar(idx).SetRange(window[0], window[1])

    # Restriction for return since 17:00
    for v_id in range(data['num_vehicles']):
        end_idx = routing.End(v_id)
        time_dim.CumulVar(end_idx).SetRange(0, MAX_WORK_MIN)

    # Find settings
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.time_limit.seconds = 10
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC

    # Start routing
    solution = routing.SolveWithParameters(params)
    if not solution:
        print("Answer doesn't exist.")
        return

    print("Schedule per day:")
    day_counter = 1
    for v_id in range(data['num_vehicles']):
        index = routing.Start(v_id)
        route = []
        while not routing.IsEnd(index):
            node = manager.IndexToNode(index)
            if node != data['depot']:
                time_var = time_dim.CumulVar(index)
                arrival_internal = solution.Value(time_var)
                label = data['headers'][node]
                route.append((label, arrival_internal))
            index = solution.Value(routing.NextVar(index))

        if route:
            print(f"\nDay {day_counter}:")
            print(f" Start work from: 08:00")
            for label, arrival_internal in route:
                arrival = WORK_START + arrival_internal
                departure = arrival + data['visit_duration']
                print(f" - {label}: arriving at {arrival//60:02d}:{arrival%60:02d}, departed at {departure//60:02d}:{departure%60:02d}")
            back_internal = solution.Value(time_dim.CumulVar(index))
            back_time = WORK_START + back_internal
            print(f" Return to base at: {back_time//60:02d}:{back_time%60:02d}")
            day_counter += 1

# Run
matrix, headers = read_matrix("sample11.csv")
model = create_model(matrix, headers)
solve_schedule(model)
