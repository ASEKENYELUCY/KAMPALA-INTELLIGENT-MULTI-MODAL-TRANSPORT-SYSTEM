import concurrent.futures

class ParallelProcessor:
    def __init__(self, num_workers=2):
        self.num_workers = num_workers
    
    def simple_parallel(self, graph, requests):
        from shortest_path import ShortestPath
        sp = ShortestPath(graph)
        
        def process_request(req):
            start, end = req
            return sp.a_star(start, end)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_workers) as executor:
            futures = [executor.submit(process_request, req) for req in requests]
            results = [f.result() for f in futures]
        
        return results