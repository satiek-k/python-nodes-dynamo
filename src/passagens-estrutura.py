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


#--------------------------------------------------------------------------------------------------------------------------------------
# Get linked document
dataEnteringNode = IN

link_inst = FilteredElementCollector(doc).OfClass(RevitLinkInstance).ToElements()
link_doc = link_inst[0].GetLinkDocument()

OUT = link_inst


#--------------------------------------------------------------------------------------------------------------------------------------
# Get all pipes from the linked document (the IN[0] is the link instance)
dataEnteringNode = IN

link_inst = UnwrapElement(IN[0])

pipes = []
for link in link_inst:
    link_id = link.GetLinkDocument()
    pipes.extend(FilteredElementCollector(link_id)
               .OfCategory(BuiltInCategory.OST_PipeCurves)
               .WhereElementIsNotElementType().ToElements())

OUT = pipes


#--------------------------------------------------------------------------------------------------------------------------------------
# Get all walls from the host document
dataEnteringNode = IN

host_walls = (FilteredElementCollector(doc)
.OfCategory(BuiltInCategory.OST_Walls)
.WhereElementIsNotElementType().ToElements())

OUT = host_walls


#--------------------------------------------------------------------------------------------------------------------------------------
# Get solids from elements (the IN[0] is the list of elements, the IN[1] is the list of elements to be processed)
dataEnteringNode = IN

def get_solids(elements):
    data = [] 
    for el in elements: 
        el = UnwrapElement(el)
        try: 
            d = el.Diameter
        except:
            d = None
        try:
            for g in el.get_Geometry(Options()): 
                if isinstance(g, Solid) and g.Volume > 0:
                    data.append((g, d))
        except Exception: 
            pass 
    return data     

wall_data = get_solids(IN[1])
pipe_data = get_solids(IN[0])
OUT = (wall_data, pipe_data)



#--------------------------------------------------------------------------------------------------------------------------------------
# Move pipe solids to the hostdocument's coordinate system (the IN[0] is the list of pipe solids, the IN[1] is the link instance)
pipe_data = IN[0][1]        

link = UnwrapElement(IN[1])[0]
transform = link.GetTotalTransform()
moved_pipes = []
for solid, d in pipe_data:
    new_solid = SolidUtils.CreateTransformed(solid, transform)
    moved_pipes.append((new_solid, d))

OUT = moved_pipes


#--------------------------------------------------------------------------------------------------------------------------------------
# Check for clashes between moved pipe solids and wall solids (the IN[0] is the list of wall solids, the IN[1] is the list of moved pipe solids)
wall_data = IN[0][1]  
moved_pipes = IN[1]

clashes = []
for pipe_solid, d in moved_pipes:
    for wall_solid, _ in wall_data:
        try:
            result = BooleanOperationsUtils.ExecuteBooleanOperation(
                pipe_solid, wall_solid, BooleanOperationsType.Intersect)
            if result.Volume > 0:
                clashes.append([pipe_solid, wall_solid, d])
        except:
            pass
            
OUT = clashes


#--------------------------------------------------------------------------------------------------------------------------------------
# Get centroids of clashes (the IN[0] is the list of clashes, each clash is a list with the pipe solid, the wall solid and the pipe diameter)
clashes = IN[0]

centroids = []
for clashe in clashes:
    pipe = clashe[0]
    wall = clashe[1]
    intersection = BooleanOperationsUtils.ExecuteBooleanOperation(
                   pipe, wall, BooleanOperationsType.Intersect)
    point = intersection.ComputeCentroid()
    centroids.append(point)

OUT = centroids


#--------------------------------------------------------------------------------------------------------------------------------------
# Create family instances at the clash centroids (the IN[0] is the list of clash centroids, the IN[1] is the family symbol to be created)
import clr
clr.AddReference('ProtoGeometry')
from Autodesk.DesignScript.Geometry import *
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Structure import StructuralType
clr.AddReference('RevitServices')
from RevitServices.Persistence import DocumentManager
from RevitServices.Transactions import TransactionManager

doc = DocumentManager.Instance.CurrentDBDocument

insert_points = IN[0]
symbol = UnwrapElement(IN[1])

TransactionManager.Instance.EnsureInTransaction(doc)

if not symbol.IsActive:
    symbol.Activate()
    doc.Regenerate()

passagem = []
for in_point in insert_points:  
    fi = doc.Create.NewFamilyInstance(in_point, symbol, StructuralType.NonStructural)
    passagem.append(fi) 

TransactionManager.Instance.TransactionTaskDone()

OUT = passagem


#--------------------------------------------------------------------------------------------------------------------------------------
# Get all generic models from the host document and check if a generic model with the same symbol already exists (the IN[0] is the symbol of the generic model to be created, unsing the Family Type node)
symbol = UnwrapElement(IN[0])

collector = (FilteredElementCollector(doc)
             .OfCategory(BuiltInCategory.OST_GenericModel)
             .WhereElementIsNotElementType()
             .ToElements())

pass_exist = [g for g in collector
              if g.IsValidObject and g.Symbol.Id == symbol.Id]

OUT = pass_exist


#----------------------------------------------------------------------------------------------------------------------------------------
# Check if the candidate points are free from existing generic models (the IN[0] is the list of existing generic models, the IN[1] is the list of candidate points to be checked)
existing_elems = UnwrapElement(IN[0])
candidate_new  = IN[1]

exist_pts = []
for p in existing_elems:
    exist_pts.append(p.Location.Point)

tol = UnitUtils.ConvertToInternalUnits(30, UnitTypeId.Centimeters)

kept_pts = list(exist_pts)
mask = []
for c in candidate_new:
    is_free = True
    for e in kept_pts:
        if c.DistanceTo(e) < tol:
            is_free = False
            break
    mask.append(is_free)
    if is_free:
        kept_pts.append(c)
        
OUT = mask
# Conect the OUT with a List.FilterByBoolMask node, using the mask to filter the candidate points from the Get centroids of clashes node, so that only the points that are free from existing generic models will be kept for the creation of new family instances.