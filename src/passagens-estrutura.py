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


#--------------------------------------------------------------------------------------------------------------------------------------
# Get all walls from the host document
dataEnteringNode = IN

host_walls = (FilteredElementCollector(doc)
.OfCategory(BuiltInCategory.OST_Walls)
.WhereElementIsNotElementType().ToElements())

OUT = host_walls


#--------------------------------------------------------------------------------------------------------------------------------------
# Get solids from elements
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
# Move pipe solids to the hostdocument's coordinate system
pipe_data = IN[0][1]        

link = UnwrapElement(IN[1])[0]
transform = link.GetTotalTransform()
moved_pipes = []
for solid, d in pipe_data:
    new_solid = SolidUtils.CreateTransformed(solid, transform)
    moved_pipes.append((new_solid, d))

OUT = moved_pipes


#--------------------------------------------------------------------------------------------------------------------------------------
# Check for clashes between moved pipe solids and wall solids
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
# Get centroids of clashes
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
# Create family instances at the clash centroids
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
# Get all generic models from the host document
dataEnteringNode = IN

generic_model = (FilteredElementCollector(doc)
.OfCategory(BuiltInCategory.OST_GenericModel)
.WhereElementIsNotElementType().ToElements())

OUT = generic_model


#--------------------------------------------------------------------------------------------------------------------------------------
# Check if a generic model with the same symbol already exists
generic_exist = UnwrapElement(IN[0])
symbol = UnwrapElement(IN[1])

pass_exist = []
for g in generic_exist:
    try:
        if g.Symbol.Id == symbol.Id:
            pass_exist.append(g)
    except:
        pass

OUT = pass_exist