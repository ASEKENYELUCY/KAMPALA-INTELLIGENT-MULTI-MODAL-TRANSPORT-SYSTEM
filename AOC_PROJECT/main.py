"""
Kampala Transport System - Web Interface
Run with: uvicorn main:app --reload
Open browser: http://localhost:8000

Main file to demonstrate the system
"""
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
import os
from typing import Optional

# Import our modules
from graph import SimpleGraph
from shortest_path import ShortestPath
from congestion import CongestionHandler
from parallel import ParallelProcessor
from heuristics import MultiStopRouter

# Setup templates
templates = Jinja2Templates(directory="templates")

# Creating Kampala graph (mock data for demo)
def create_kampala_graph():
    """Create a simple graph of Kampala"""
    graph = SimpleGraph()
    
    # Adding major locations in Kampala with coordinates
    locations = {
        "Old Taxi Park": (0.3146, 32.5761),
        "Garden City": (0.3191, 32.5836),
        "Nakasero Market": (0.3175, 32.5800),
        "Kisekka Market": (0.3130, 32.5780),
        "Owino Market": (0.3120, 32.5750),
        "Wandegeya": (0.3270, 32.5690),
        "Makerere University": (0.3381, 32.5696),
        "Nakawa": (0.3250, 32.6100),
        "Bugolobi": (0.3220, 32.6200),
        "Kampala Road": (0.3170, 32.5820),
        "Jinja Road": (0.3200, 32.5900),
        "Entebbe Road": (0.3050, 32.5700),
        "Bwaise": (0.3500, 32.5600),
        "Lugogo": (0.3300, 32.6000),
        "Kabalagala": (0.3100, 32.5900)
    }
    
    # Add nodes
    for i, (name, (lat, lon)) in enumerate(locations.items()):
        graph.add_node(i, lat, lon)
    
    # Add roads (simplified)
    roads = [
        (0, 1, 5),   # Old Taxi Park -> Garden City
        (0, 2, 3),   # Old Taxi Park -> Nakasero
        (2, 1, 4),   # Nakasero -> Garden City
        (0, 3, 2),   # Old Taxi Park -> Kisekka
        (3, 4, 3),   # Kisekka -> Owino
        (2, 5, 8),   # Nakasero -> Wandegeya
        (5, 6, 4),   # Wandegeya -> Makerere
        (1, 7, 10),  # Garden City -> Nakawa
        (7, 8, 6),   # Nakawa -> Bugolobi
        (1, 9, 2),   # Garden City -> Kampala Road
        (9, 10, 5),  # Kampala Road -> Jinja Road
        (10, 11, 8), # Jinja Road -> Entebbe Road
        (6, 12, 12), # Makerere -> Bwaise
        (7, 13, 4),  # Nakawa -> Lugogo
        (1, 14, 7),  # Garden City -> Kabalagala
    ]
    
    for from_node, to_node, time in roads:
        graph.add_edge(from_node, to_node, time)
    
    return graph, locations

# Create global instances
graph, locations = create_kampala_graph()
sp = ShortestPath(graph)
ch = CongestionHandler(graph)
pp = ParallelProcessor(num_workers=4)
msr = MultiStopRouter(graph)

# Create FastAPI app (was missing, caused NameError)
app = FastAPI(title="KAMPALA INTELLIGENT MULTI-MODAL TRANSPORT SYSTEM", version="1.0")
# Optionally mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/locations")
async def get_locations():
    """Get list of locations in Kampala"""
    location_list = [{"id": i, "name": name, "lat": lat, "lon": lon}
                     for i, (name, (lat, lon)) in enumerate(locations.items())]
    return {"locations": location_list}

@app.post("/api/route")
async def calculate_route(
    start: int = Form(...),
    end: int = Form(...),
    algorithm: str = Form("astar")
):
    """Calculate route between two locations"""
    try:
        start = int(start)
        end = int(end)

        if algorithm =="dijkstra":
            path, time = sp.dijkstra(start, end)
        else: # A* by default
            path, time = sp.a_star(start, end)

        # Convert path to location names
        path_names = [list(locations.keys())[node_id] for node_id in path]

        return {
            "success": True,
            "path": path,
            "path_names": path_names,
            "time": round(time, 2),
            "algorithm": algorithm,
            "distance": len(path)-1 # number of road segments
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    
@app.post("/api/multi_stop")
async def multi_stop_route(stops: str = Form(...)):
    """Calculate multi-stop route using simulated annealing"""
    try:
        stops_list = json.loads(stops) # [start, stop1, stop2, ..., end]

        # Convert to node IDs
        stop_ids = [int(s) for s in stops_list]

        # Using greedy algorithm
        route, time = msr.greedy_tsp(stops_list)

        route_names = [list(locations.keys())[node_id] for node_id in route]

        return {
            "success": True,
            "route": route,
            "route_names": route_names,
            "time": round(time, 2),
            "stops": len(stops_list)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
    
@app.get("/api/congestion/{road_id}")
async def get_congestion(road_id: str):
    """Get congestion alternatives for a road"""
    try:
        start, end = map(int, road_id.split("-"))
        alternatives = ch.find_alternative_routes((start, end), vehicles_to_redirect=50)
        
        result = []
        for alt in alternatives:
            alt_path_names = [list(locations.keys())[node_id] for node_id in alt['path']]
            result.append({
                "path": alt['path'],
                "path_names": alt_path_names,
                "time": round(alt['time'], 2),
                "capacity": alt['capacity']
            })
        
        return {"success": True, "alternatives": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/batch-routes")
async def batch_routes(requests: str = Form(...)):
    """Process multiple routes in parallel"""
    try:
        requests_list = json.loads(requests)  # [[start1, end1], [start2, end2], ...]
        
        # Process in parallel
        results = pp.simple_parallel(graph, requests_list)
        
        response = []
        for i, (path, time) in enumerate(results):
            path_names = [list(locations.keys())[node_id] for node_id in path]
            response.append({
                "request_id": i,
                "path": path,
                "path_names": path_names,
                "time": round(time, 2)
            })
        
        return {"success": True, "results": response}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/graph-data")
async def get_graph_data():
    """Get graph data for visualization"""
    nodes = []
    for i, (name, (lat, lon)) in enumerate(locations.items()):
        nodes.append({
            "id": i,
            "name": name,
            "lat": lat,
            "lon": lon,
            "x": (lon - 32.56) * 1000,  # Scale for visualization
            "y": (lat - 0.30) * 1000
        })
    
    edges = []
    for i in range(len(locations)):
        for neighbor, weight in graph.get_neighbors(i):
            edges.append({
                "from": i,
                "to": neighbor,
                "weight": weight
            })
    
    return {"nodes": nodes, "edges": edges}

# Create templates directory if it doesn't exist
os.makedirs("templates", exist_ok=True)

# Create HTML template
with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Kampala Transport System</title>
    <script src="https://cdn.plot.ly/plotly-2.24.1.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        header {
            text-align: center;
            margin-bottom: 30px;
            color: white;
        }
        
        h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        
        .main-content {
            display: grid;
            grid-template-columns: 300px 1fr;
            gap: 20px;
        }
        
        .sidebar {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        
        .graph-container {
            background: white;
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            height: 600px;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #555;
        }
        
        select, input, button {
            width: 100%;
            padding: 12px;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        select:focus, input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            cursor: pointer;
            font-weight: 600;
            letter-spacing: 1px;
            margin-top: 5px;
        }
        
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        }
        
        .results {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            max-height: 300px;
            overflow-y: auto;
        }
        
        .result-item {
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
        }
        
        .route-path {
            font-family: monospace;
            background: #f1f3f4;
            padding: 8px;
            border-radius: 5px;
            margin: 10px 0;
            font-size: 14px;
        }
        
        .time-badge {
            background: #667eea;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 14px;
            display: inline-block;
            margin-top: 5px;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .control-btn {
            flex: 1;
            padding: 10px;
            background: #f8f9fa;
            border: 2px solid #e1e5e9;
            border-radius: 10px;
            cursor: pointer;
            text-align: center;
            transition: all 0.3s;
        }
        
        .control-btn.active {
            background: #667eea;
            color: white;
            border-color: #667eea;
        }
        
        @media (max-width: 768px) {
            .main-content {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🚗 KAMPALA INTELLIGENT MULTI-MODAL TRANSPORT SYSTEM</h1>
            <p class="subtitle">Intelligent Multi-Modal Route Optimization</p>
        </header>
        
        <div class="main-content">
            <div class="sidebar">
                <div class="controls">
                    <div class="control-btn active" onclick="showTab('route')">Route</div>
                    <div class="control-btn" onclick="showTab('multi')">Multi-Stop</div>
                    <div class="control-btn" onclick="showTab('congestion')">Congestion</div>
                    <div class="control-btn" onclick="showTab('batch')">Batch</div>
                </div>
                
                <!-- Route Tab -->
                <div id="route-tab" class="tab-content">
                    <h3>Find Shortest Route</h3>
                    <div class="form-group">
                        <label for="start">Start Location</label>
                        <select id="start">
                            <option value="">Select start location...</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="end">Destination</label>
                        <select id="end">
                            <option value="">Select destination...</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="algorithm">Algorithm</label>
                        <select id="algorithm">
                            <option value="astar">A* Search (Fastest)</option>
                            <option value="dijkstra">Dijkstra (Guaranteed)</option>
                        </select>
                    </div>
                    
                    <button onclick="calculateRoute()">Find Route</button>
                </div>
                
                <!-- Multi-Stop Tab -->
                <div id="multi-tab" class="tab-content" style="display: none;">
                    <h3>Multi-Stop Route</h3>
                    <div class="form-group">
                        <label>Select Stops (in order):</label>
                        <div id="multi-stops">
                            <select class="stop-select" onchange="updateMultiRoute()">
                                <option value="">Select stop...</option>
                            </select>
                        </div>
                        <button onclick="addStop()" style="margin-top: 10px;">+ Add Stop</button>
                    </div>
                    <button onclick="calculateMultiRoute()">Calculate Multi-Stop Route</button>
                </div>
                
                <!-- Congestion Tab -->
                <div id="congestion-tab" class="tab-content" style="display: none;">
                    <h3>Congestion Management</h3>
                    <div class="form-group">
                        <label for="congested-road">Select Congested Road</label>
                        <select id="congested-road">
                            <option value="">Select road...</option>
                        </select>
                    </div>
                    <button onclick="checkCongestion()">Find Alternatives</button>
                </div>
                
                <!-- Batch Tab -->
                <div id="batch-tab" class="tab-content" style="display: none;">
                    <h3>Batch Route Processing</h3>
                    <p>Process multiple routes in parallel</p>
                    <div id="batch-requests">
                        <div class="batch-request">
                            <select class="batch-start">
                                <option value="">Start...</option>
                            </select>
                            <select class="batch-end">
                                <option value="">End...</option>
                            </select>
                        </div>
                    </div>
                    <button onclick="addBatchRequest()" style="margin: 10px 0;">+ Add Request</button>
                    <button onclick="processBatch()">Process Batch</button>
                </div>
                
                <!-- Results -->
                <div id="results" class="results">
                    <h4>Results will appear here</h4>
                    <p>Select a function and click calculate</p>
                </div>
            </div>
            
            <div class="graph-container">
                <div id="graph"></div>
            </div>
        </div>
    </div>

    <script>
        let locations = [];
        let currentRoute = [];
        let currentMode = 'route';
        
        // Initialize
        document.addEventListener('DOMContentLoaded', async function() {
            await loadLocations();
            initializeGraph();
            showTab('route');
        });
        
        async function loadLocations() {
            try {
                const response = await fetch('/api/locations');
                const data = await response.json();
                locations = data.locations;
                
                // Populate dropdowns
                const selectElements = document.querySelectorAll('select:not(.stop-select):not(.batch-start):not(.batch-end)');
                selectElements.forEach(select => {
                    // Clear existing options except first
                    while (select.options.length > 1) {
                        select.remove(1);
                    }
                    
                    // Add locations
                    locations.forEach(loc => {
                        const option = document.createElement('option');
                        option.value = loc.id;
                        option.textContent = loc.name;
                        select.appendChild(option);
                    });
                });
                
                // Also populate specialized dropdowns
                populateSpecialDropdowns();
                
            } catch (error) {
                console.error('Error loading locations:', error);
            }
        }
        
        function populateSpecialDropdowns() {
            // Roads for congestion tab
            const roads = [
                "0-1", "0-2", "2-1", "0-3", "3-4",
                "2-5", "5-6", "1-7", "7-8", "1-9"
            ];
            
            const roadSelect = document.getElementById('congested-road');
            roads.forEach(road => {
                const [start, end] = road.split('-');
                const startName = locations.find(l => l.id == start)?.name || start;
                const endName = locations.find(l => l.id == end)?.name || end;
                const option = document.createElement('option');
                option.value = road;
                option.textContent = `${startName} → ${endName}`;
                roadSelect.appendChild(option);
            });
        }
        
        function showTab(tabName) {
            // Update controls
            document.querySelectorAll('.control-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Show selected tab
            document.querySelectorAll('.tab-content').forEach(tab => {
                tab.style.display = 'none';
            });
            document.getElementById(`${tabName}-tab`).style.display = 'block';
            
            currentMode = tabName;
        }
        
        async function calculateRoute() {
            const start = document.getElementById('start').value;
            const end = document.getElementById('end').value;
            const algorithm = document.getElementById('algorithm').value;
            
            if (!start || !end) {
                showError('Please select both start and end locations');
                return;
            }
            
            const formData = new FormData();
            formData.append('start', start);
            formData.append('end', end);
            formData.append('algorithm', algorithm);
            
            try {
                const response = await fetch('/api/route', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    displayRouteResult(result);
                    currentRoute = result.path;
                    updateGraph(result.path);
                } else {
                    showError(result.error);
                }
            } catch (error) {
                showError('Error calculating route: ' + error.message);
            }
        }
        
        async function calculateMultiRoute() {
            const stopSelects = document.querySelectorAll('.stop-select');
            const stops = Array.from(stopSelects)
                .map(select => select.value)
                .filter(value => value !== '');
            
            if (stops.length < 2) {
                showError('Please select at least 2 stops');
                return;
            }
            
            const formData = new FormData();
            formData.append('stops', JSON.stringify(stops));
            
            try {
                const response = await fetch('/api/multi-stop', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    displayMultiRouteResult(result);
                    currentRoute = result.route;
                    updateGraph(result.route);
                } else {
                    showError(result.error);
                }
            } catch (error) {
                showError('Error calculating multi-stop route: ' + error.message);
            }
        }
        
        async function checkCongestion() {
            const road = document.getElementById('congested-road').value;
            
            if (!road) {
                showError('Please select a road');
                return;
            }
            
            try {
                const response = await fetch(`/api/congestion/${road}`);
                const result = await response.json();
                
                if (result.success) {
                    displayCongestionResult(result);
                } else {
                    showError(result.error);
                }
            } catch (error) {
                showError('Error checking congestion: ' + error.message);
            }
        }
        
        async function processBatch() {
            const batchDivs = document.querySelectorAll('.batch-request');
            const requests = [];
            
            batchDivs.forEach(div => {
                const start = div.querySelector('.batch-start').value;
                const end = div.querySelector('.batch-end').value;
                
                if (start && end) {
                    requests.push([parseInt(start), parseInt(end)]);
                }
            });
            
            if (requests.length === 0) {
                showError('Please add at least one valid request');
                return;
            }
            
            const formData = new FormData();
            formData.append('requests', JSON.stringify(requests));
            
            try {
                const response = await fetch('/api/batch-routes', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (result.success) {
                    displayBatchResult(result);
                } else {
                    showError(result.error);
                }
            } catch (error) {
                showError('Error processing batch: ' + error.message);
            }
        }
        
        function displayRouteResult(result) {
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = `
                <h4>Route Found!</h4>
                <div class="result-item">
                    <strong>Path:</strong>
                    <div class="route-path">${result.path_names.join(' → ')}</div>
                    <div class="time-badge">${result.time} minutes</div>
                    <div><small>Algorithm: ${result.algorithm.toUpperCase()}</small></div>
                    <div><small>Distance: ${result.distance} road segments</small></div>
                </div>
            `;
        }
        
        function displayMultiRouteResult(result) {
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = `
                <h4>Multi-Stop Route Found!</h4>
                <div class="result-item">
                    <strong>Optimal Route:</strong>
                    <div class="route-path">${result.route_names.join(' → ')}</div>
                    <div class="time-badge">${result.time} minutes total</div>
                    <div><small>Stops: ${result.stops} locations</small></div>
                </div>
            `;
        }
        
        function displayCongestionResult(result) {
            const resultsDiv = document.getElementById('results');
            let html = `<h4>Alternative Routes Found</h4>`;
            
            result.alternatives.forEach((alt, index) => {
                html += `
                    <div class="result-item">
                        <strong>Alternative ${index + 1}:</strong>
                        <div class="route-path">${alt.path_names.join(' → ')}</div>
                        <div class="time-badge">${alt.time} minutes</div>
                        <div><small>Capacity: ${alt.capacity} vehicles/hour</small></div>
                    </div>
                `;
            });
            
            resultsDiv.innerHTML = html;
        }
        
        function displayBatchResult(result) {
            const resultsDiv = document.getElementById('results');
            let html = `<h4>Batch Processing Complete</h4>`;
            
            result.results.forEach((res, index) => {
                html += `
                    <div class="result-item">
                        <strong>Request ${index + 1}:</strong>
                        <div class="route-path">${res.path_names.join(' → ')}</div>
                        <div class="time-badge">${res.time} minutes</div>
                    </div>
                `;
            });
            
            html += `<p><small>Processed ${result.results.length} routes in parallel</small></p>`;
            resultsDiv.innerHTML = html;
        }
        
        function showError(message) {
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = `
                <div style="color: #e74c3c; background: #ffeaea; padding: 15px; border-radius: 8px; border-left: 4px solid #e74c3c;">
                    <strong>Error:</strong> ${message}
                </div>
            `;
        }
        
        function addStop() {
            const stopsDiv = document.getElementById('multi-stops');
            const select = document.createElement('select');
            select.className = 'stop-select';
            select.onchange = updateMultiRoute;
            
            const defaultOption = document.createElement('option');
            defaultOption.value = '';
            defaultOption.textContent = 'Select stop...';
            select.appendChild(defaultOption);
            
            locations.forEach(loc => {
                const option = document.createElement('option');
                option.value = loc.id;
                option.textContent = loc.name;
                select.appendChild(option);
            });
            
            stopsDiv.appendChild(select);
        }
        
        function addBatchRequest() {
            const batchDiv = document.getElementById('batch-requests');
            const requestDiv = document.createElement('div');
            requestDiv.className = 'batch-request';
            requestDiv.style.display = 'flex';
            requestDiv.style.gap = '10px';
            requestDiv.style.marginBottom = '10px';
            
            const startSelect = document.createElement('select');
            startSelect.className = 'batch-start';
            
            const endSelect = document.createElement('select');
            endSelect.className = 'batch-end';
            
            // Add default options
            [startSelect, endSelect].forEach(select => {
                const defaultOption = document.createElement('option');
                defaultOption.value = '';
                defaultOption.textContent = select.className.includes('start') ? 'Start...' : 'End...';
                select.appendChild(defaultOption);
                
                locations.forEach(loc => {
                    const option = document.createElement('option');
                    option.value = loc.id;
                    option.textContent = loc.name;
                    select.appendChild(option);
                });
            });
            
            requestDiv.appendChild(startSelect);
            requestDiv.appendChild(endSelect);
            batchDiv.appendChild(requestDiv);
        }
        
        function updateMultiRoute() {
            // This could show a preview of selected stops
        }
        
        // Graph visualization
        function initializeGraph() {
            fetch('/api/graph-data')
                .then(response => response.json())
                .then(data => {
                    drawGraph(data);
                });
        }
        
        function drawGraph(graphData) {
            const traceNodes = {
                x: graphData.nodes.map(node => node.x),
                y: graphData.nodes.map(node => node.y),
                mode: 'markers+text',
                type: 'scatter',
                text: graphData.nodes.map(node => node.name),
                textposition: 'top center',
                marker: {
                    size: 12,
                    color: '#667eea',
                    line: {
                        width: 2,
                        color: '#ffffff'
                    }
                },
                name: 'Locations',
                hoverinfo: 'text'
            };
            
            // Create edge traces
            const edgeTraces = graphData.edges.map(edge => {
                const fromNode = graphData.nodes.find(n => n.id == edge.from);
                const toNode = graphData.nodes.find(n => n.id == edge.to);
                
                return {
                    x: [fromNode.x, toNode.x, null],
                    y: [fromNode.y, toNode.y, null],
                    mode: 'lines',
                    type: 'scatter',
                    line: {
                        width: 2,
                        color: '#ccc'
                    },
                    hoverinfo: 'none',
                    showlegend: false
                };
            });
            
            const layout = {
                title: 'Kampala Road Network',
                showlegend: false,
                hovermode: 'closest',
                margin: { t: 30, b: 20, l: 20, r: 20 },
                xaxis: {
                    showgrid: false,
                    zeroline: false,
                    showticklabels: false
                },
                yaxis: {
                    showgrid: false,
                    zeroline: false,
                    showticklabels: false
                },
                plot_bgcolor: '#f8f9fa',
                paper_bgcolor: '#f8f9fa'
            };
            
            Plotly.newPlot('graph', [traceNodes, ...edgeTraces], layout);
        }
        
        function updateGraph(route) {
            if (!route || route.length < 2) return;
            
            fetch('/api/graph-data')
                .then(response => response.json())
                .then(data => {
                    // Create highlighted route trace
                    const routeX = [];
                    const routeY = [];
                    
                    route.forEach(nodeId => {
                        const node = data.nodes.find(n => n.id == nodeId);
                        if (node) {
                            routeX.push(node.x);
                            routeY.push(node.y);
                        }
                    });
                    
                    const routeTrace = {
                        x: routeX,
                        y: routeY,
                        mode: 'lines+markers',
                        type: 'scatter',
                        line: {
                            width: 4,
                            color: '#00b894'
                        },
                        marker: {
                            size: 10,
                            color: '#00b894'
                        },
                        name: 'Selected Route',
                        hoverinfo: 'none'
                    };
                    
                    // Redraw graph with highlighted route
                    drawGraph(data);
                    
                    // Add route trace
                    Plotly.addTraces('graph', routeTrace);
                });
        }
    </script>
</body>
</html>
    """)

print("HTML template created successfully!")