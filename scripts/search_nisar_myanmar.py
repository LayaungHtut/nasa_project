import asf_search as asf
import json, sys

# Myanmar bounding box (whole country) for broad first pass
myanmar_wkt = "POLYGON((92.0 9.5,101.5 9.5,101.5 28.6,92.0 28.6,92.0 9.5))"

print("asf_search version:", asf.__version__)
print("Searching NISAR GCOV over Myanmar bbox...")

try:
    results = asf.search(
        platform=["NISAR"],
        processingLevel=["GCOV"],
        intersectsWith=myanmar_wkt,
        maxResults=250,
    )
    print(f"Total results: {len(results)}")
    out = []
    for r in results:
        p = r.properties
        g = r.geometry
        out.append({
            "fileID": p.get("fileID"),
            "sceneName": p.get("sceneName"),
            "startTime": p.get("startTime"),
            "stopTime": p.get("stopTime"),
            "platform": p.get("platform"),
            "processingLevel": p.get("processingLevel"),
            "polarization": p.get("polarization"),
            "pathNumber": p.get("pathNumber"),
            "frameNumber": p.get("frameNumber"),
            "bytes": p.get("bytes"),
            "url": p.get("url"),
            "geometry": g,
        })
    with open("myanmar_nisar_gcov_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print("Wrote myanmar_nisar_gcov_results.json")
    for o in out[:20]:
        print(o["fileID"], o["startTime"], o["polarization"], o["bytes"])
except Exception as e:
    print("ERROR:", type(e).__name__, str(e), file=sys.stderr)
    raise
