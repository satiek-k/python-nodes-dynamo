# Libraries DesignScript
import sys
import clr
clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *

clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

clr.AddReference('RevitServices')
from RevitServices.Persistence import DocumentManager
doc = DocumentManager.Instance.CurrentDBDocument



# Get linked document
dataEnteringNode = IN

link_inst = FilteredElementCollector(doc).OfClass(RevitLinkInstance).ToElements()
link_doc = link_inst[0].GetLinkDocument()

OUT = link_inst



# Get all pipes from the linked document
dataEnteringNode = IN

link_inst = UnwrapElement(IN[0])

pipes = []
for link in link_inst:
    link_id = link.GetLinkDocument()
    pipes.extend(FilteredElementCollector(link_id)
               .OfCategory(BuiltInCategory.OST_PipeCurves)
               .WhereElementIsNotElementType().ToElements())

OUT = pipes



# Get all walls from the host document
dataEnteringNode = IN

host_walls = (FilteredElementCollector(doc)
.OfCategory(BuiltInCategory.OST_Walls)
.WhereElementIsNotElementType().ToElements())

OUT = host_walls



# Get solids from elements
dataEnteringNode = IN

def get_solids(elements):
    solids = [] 
    for el in elements: 
        el = UnwrapElement(el)
        try:
            geometry = el.get_Geometry(Options())
            for g in geometry: 
                if isinstance(g, Solid) and g.Volume > 0:
                    solids.append(g)
        except Exception: 
            pass 
    return solids     

wall_solids = get_solids(IN[0])
pipe_solids = get_solids(IN[1])
OUT = pipe_solids, wall_solids 



# Move pipe solids to the hostdocument's coordinate system
pipe_solids = IN[0][0]    
wall_solids = IN[0][1]     

link = UnwrapElement(IN[1])[0]
transform = link.GetTotalTransform()
moved_pipes = []
for s in pipe_solids:
    new_solid = SolidUtils.CreateTransformed(s, transform)
    moved_pipes.append(new_solid)

OUT = moved_pipes



# Check for clashes between moved pipe solids and wall solids
   
wall_solids = IN[0][1]  
moved_pipes = IN[1]

clashes = []
for pipe in moved_pipes:
    for wall in wall_solids:
        try:
            result = BooleanOperationsUtils.ExecuteBooleanOperation(
                pipe, wall, BooleanOperationsType.Intersect)
            if result.Volume > 0:
                clashes.append([pipe, wall])
        except:
            pass
            
OUT = clashes