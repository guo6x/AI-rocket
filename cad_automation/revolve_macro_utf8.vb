' NX 12.0.2.9
' NX journal for the Ad Astra CAD workflow.

'
Imports System
Imports NXOpen

Module NXJournal
Sub Main (ByVal args() As String) 

Dim theSession As NXOpen.Session = NXOpen.Session.GetSession()
Dim markId1 As NXOpen.Session.UndoMarkId = Nothing
markId1 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "加载部件")

Dim basePart1 As NXOpen.BasePart = Nothing
Dim partLoadStatus1 As NXOpen.PartLoadStatus = Nothing
basePart1 = theSession.Parts.OpenActiveDisplay("D:\AI_rocket\cad_automation\ad_astra_test.prt", NXOpen.DisplayPartOption.AllowAdditional, partLoadStatus1)

Dim workPart As NXOpen.Part = theSession.Parts.Work

Dim displayPart As NXOpen.Part = theSession.Parts.Display

partLoadStatus1.Dispose()
theSession.ApplicationSwitchImmediate("UG_APP_GATEWAY")

Dim scaleAboutPoint1 As NXOpen.Point3d = New NXOpen.Point3d(-61.997370727432056, 54.651183172655585, 0.0)
Dim viewCenter1 As NXOpen.Point3d = New NXOpen.Point3d(61.997370727432056, -54.651183172655585, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint1, viewCenter1)

Dim partCloseResponses1 As NXOpen.PartCloseResponses = Nothing
partCloseResponses1 = theSession.Parts.NewPartCloseResponses()

workPart.Close(NXOpen.BasePart.CloseWholeTree.False, NXOpen.BasePart.CloseModified.UseResponses, partCloseResponses1)

workPart = Nothing
displayPart = Nothing
partCloseResponses1.Dispose()
theSession.ApplicationSwitchImmediate("UG_APP_NOPART")

' ----------------------------------------------
'   菜单：文件(F)->新建(N)...
' ----------------------------------------------
Dim markId2 As NXOpen.Session.UndoMarkId = Nothing
markId2 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "开始")

Dim fileNew1 As NXOpen.FileNew = Nothing
fileNew1 = theSession.Parts.FileNew()

theSession.SetUndoMarkName(markId2, "新建 对话框")

Dim markId3 As NXOpen.Session.UndoMarkId = Nothing
markId3 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "新建")

theSession.DeleteUndoMark(markId3, Nothing)

Dim markId4 As NXOpen.Session.UndoMarkId = Nothing
markId4 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "新建")

fileNew1.TemplateFileName = "model-plain-1-mm-template.prt"

fileNew1.UseBlankTemplate = False

fileNew1.ApplicationName = "ModelTemplate"

fileNew1.Units = NXOpen.Part.Units.Millimeters

fileNew1.RelationType = ""

fileNew1.UsesMasterModel = "No"

fileNew1.TemplateType = NXOpen.FileNewTemplateType.Item

fileNew1.TemplatePresentationName = "模型"

fileNew1.ItemType = ""

fileNew1.Specialization = ""

fileNew1.SetCanCreateAltrep(False)

fileNew1.NewFileName = System.IO.Path.Combine(System.Environment.GetFolderPath(System.Environment.SpecialFolder.Desktop), "_model1.prt")

fileNew1.MasterFileName = ""

fileNew1.MakeDisplayedPart = True

fileNew1.DisplayPartOption = NXOpen.DisplayPartOption.AllowAdditional

Dim nXObject1 As NXOpen.NXObject = Nothing
nXObject1 = fileNew1.Commit()

workPart = theSession.Parts.Work ' _model1
displayPart = theSession.Parts.Display ' _model1
theSession.DeleteUndoMark(markId4, Nothing)

fileNew1.Destroy()

theSession.ApplicationSwitchImmediate("UG_APP_MODELING")

' ----------------------------------------------
'   菜单：插入(S)->曲线(C)->艺术样条(D)...
' ----------------------------------------------
Dim markId5 As NXOpen.Session.UndoMarkId = Nothing
markId5 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "开始")

Dim nullNXOpen_NXObject As NXOpen.NXObject = Nothing

Dim studioSplineBuilderEx1 As NXOpen.Features.StudioSplineBuilderEx = Nothing
studioSplineBuilderEx1 = workPart.Features.CreateStudioSplineBuilderEx(nullNXOpen_NXObject)

Dim origin1 As NXOpen.Point3d = New NXOpen.Point3d(0.0, 0.0, 0.0)
Dim normal1 As NXOpen.Vector3d = New NXOpen.Vector3d(0.0, 0.0, 1.0)
Dim plane1 As NXOpen.Plane = Nothing
plane1 = workPart.Planes.CreatePlane(origin1, normal1, NXOpen.SmartObject.UpdateOption.WithinModeling)

studioSplineBuilderEx1.DrawingPlane = plane1

Dim unit1 As NXOpen.Unit = Nothing
unit1 = studioSplineBuilderEx1.Extender.StartValue.Units

Dim expression1 As NXOpen.Expression = Nothing
expression1 = workPart.Expressions.CreateSystemExpressionWithUnits("0", unit1)

Dim expression2 As NXOpen.Expression = Nothing
expression2 = workPart.Expressions.CreateSystemExpressionWithUnits("0", unit1)

Dim origin2 As NXOpen.Point3d = New NXOpen.Point3d(0.0, 0.0, 0.0)
Dim normal2 As NXOpen.Vector3d = New NXOpen.Vector3d(0.0, 0.0, 1.0)
Dim plane2 As NXOpen.Plane = Nothing
plane2 = workPart.Planes.CreatePlane(origin2, normal2, NXOpen.SmartObject.UpdateOption.WithinModeling)

studioSplineBuilderEx1.MovementPlane = plane2

Dim expression3 As NXOpen.Expression = Nothing
expression3 = workPart.Expressions.CreateSystemExpressionWithUnits("0", unit1)

Dim expression4 As NXOpen.Expression = Nothing
expression4 = workPart.Expressions.CreateSystemExpressionWithUnits("0", unit1)

studioSplineBuilderEx1.OrientExpress.ReferenceOption = NXOpen.GeometricUtilities.OrientXpressBuilder.Reference.WcsDisplayPart

theSession.SetUndoMarkName(markId5, "艺术样条 对话框")

studioSplineBuilderEx1.MatchKnotsType = NXOpen.Features.StudioSplineBuilderEx.MatchKnotsTypes.None

studioSplineBuilderEx1.OrientExpress.AxisOption = NXOpen.GeometricUtilities.OrientXpressBuilder.Axis.Passive

studioSplineBuilderEx1.OrientExpress.PlaneOption = NXOpen.GeometricUtilities.OrientXpressBuilder.Plane.Passive

Dim markId6 As NXOpen.Session.UndoMarkId = Nothing
markId6 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

theSession.DeleteUndoMark(markId6, Nothing)

Dim markId7 As NXOpen.Session.UndoMarkId = Nothing
markId7 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

Dim coordinates1 As NXOpen.Point3d = New NXOpen.Point3d(-71.741900926500819, -63.129281379192406, 38.995401908082478)
Dim point1 As NXOpen.Point = Nothing
point1 = workPart.Points.CreatePoint(coordinates1)

Dim geometricConstraintData1 As NXOpen.Features.GeometricConstraintData = Nothing
geometricConstraintData1 = studioSplineBuilderEx1.ConstraintManager.CreateGeometricConstraintData()

geometricConstraintData1.Point = point1

studioSplineBuilderEx1.ConstraintManager.Append(geometricConstraintData1)

theSession.SetUndoMarkName(markId7, "艺术样条 - 选择")

theSession.SetUndoMarkVisibility(markId7, Nothing, NXOpen.Session.MarkVisibility.Visible)

theSession.SetUndoMarkVisibility(markId5, Nothing, NXOpen.Session.MarkVisibility.Invisible)

Dim markId8 As NXOpen.Session.UndoMarkId = Nothing
markId8 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

Dim coordinates2 As NXOpen.Point3d = New NXOpen.Point3d(-24.512920921869554, -0.99000216873899149, 45.39586301153674)
Dim point2 As NXOpen.Point = Nothing
point2 = workPart.Points.CreatePoint(coordinates2)

Dim geometricConstraintData2 As NXOpen.Features.GeometricConstraintData = Nothing
geometricConstraintData2 = studioSplineBuilderEx1.ConstraintManager.CreateGeometricConstraintData()

geometricConstraintData2.Point = point2

studioSplineBuilderEx1.ConstraintManager.Append(geometricConstraintData2)

theSession.SetUndoMarkName(markId8, "艺术样条 - 选择")

theSession.SetUndoMarkVisibility(markId8, Nothing, NXOpen.Session.MarkVisibility.Visible)

theSession.SetUndoMarkVisibility(markId5, Nothing, NXOpen.Session.MarkVisibility.Invisible)

Dim markId9 As NXOpen.Session.UndoMarkId = Nothing
markId9 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

Dim coordinates3 As NXOpen.Point3d = New NXOpen.Point3d(13.7336900022321, 35.813463260771222, 29.513237310372471)
Dim point3 As NXOpen.Point = Nothing
point3 = workPart.Points.CreatePoint(coordinates3)

Dim geometricConstraintData3 As NXOpen.Features.GeometricConstraintData = Nothing
geometricConstraintData3 = studioSplineBuilderEx1.ConstraintManager.CreateGeometricConstraintData()

geometricConstraintData3.Point = point3

studioSplineBuilderEx1.ConstraintManager.Append(geometricConstraintData3)

theSession.SetUndoMarkName(markId9, "艺术样条 - 选择")

theSession.SetUndoMarkVisibility(markId9, Nothing, NXOpen.Session.MarkVisibility.Visible)

theSession.SetUndoMarkVisibility(markId5, Nothing, NXOpen.Session.MarkVisibility.Invisible)

Dim markId10 As NXOpen.Session.UndoMarkId = Nothing
markId10 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

Dim coordinates4 As NXOpen.Point3d = New NXOpen.Point3d(69.547813669625896, 75.796932443878347, -15.052936298864623)
Dim point4 As NXOpen.Point = Nothing
point4 = workPart.Points.CreatePoint(coordinates4)

Dim geometricConstraintData4 As NXOpen.Features.GeometricConstraintData = Nothing
geometricConstraintData4 = studioSplineBuilderEx1.ConstraintManager.CreateGeometricConstraintData()

geometricConstraintData4.Point = point4

studioSplineBuilderEx1.ConstraintManager.Append(geometricConstraintData4)

theSession.SetUndoMarkName(markId10, "艺术样条 - 选择")

theSession.SetUndoMarkVisibility(markId10, Nothing, NXOpen.Session.MarkVisibility.Visible)

theSession.SetUndoMarkVisibility(markId5, Nothing, NXOpen.Session.MarkVisibility.Invisible)

Dim markId11 As NXOpen.Session.UndoMarkId = Nothing
markId11 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

Dim coordinates5 As NXOpen.Point3d = New NXOpen.Point3d(55.027335663887193, 93.549940186429581, 40.417726597738984)
Dim point5 As NXOpen.Point = Nothing
point5 = workPart.Points.CreatePoint(coordinates5)

Dim geometricConstraintData5 As NXOpen.Features.GeometricConstraintData = Nothing
geometricConstraintData5 = studioSplineBuilderEx1.ConstraintManager.CreateGeometricConstraintData()

geometricConstraintData5.Point = point5

studioSplineBuilderEx1.ConstraintManager.Append(geometricConstraintData5)

theSession.SetUndoMarkName(markId11, "艺术样条 - 选择")

theSession.SetUndoMarkVisibility(markId11, Nothing, NXOpen.Session.MarkVisibility.Visible)

theSession.SetUndoMarkVisibility(markId5, Nothing, NXOpen.Session.MarkVisibility.Invisible)

Dim markId12 As NXOpen.Session.UndoMarkId = Nothing
markId12 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

Dim coordinates6 As NXOpen.Point3d = New NXOpen.Point3d(47.432746027322487, 105.66637393175762, 73.842356804666792)
Dim point6 As NXOpen.Point = Nothing
point6 = workPart.Points.CreatePoint(coordinates6)

Dim geometricConstraintData6 As NXOpen.Features.GeometricConstraintData = Nothing
geometricConstraintData6 = studioSplineBuilderEx1.ConstraintManager.CreateGeometricConstraintData()

geometricConstraintData6.Point = point6

studioSplineBuilderEx1.ConstraintManager.Append(geometricConstraintData6)

theSession.SetUndoMarkName(markId12, "艺术样条 - 选择")

theSession.SetUndoMarkVisibility(markId12, Nothing, NXOpen.Session.MarkVisibility.Visible)

theSession.SetUndoMarkVisibility(markId5, Nothing, NXOpen.Session.MarkVisibility.Invisible)

Dim markId13 As NXOpen.Session.UndoMarkId = Nothing
markId13 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

Dim coordinates7 As NXOpen.Point3d = New NXOpen.Point3d(87.767662642255743, 152.64157602014143, 69.812436850640026)
Dim point7 As NXOpen.Point = Nothing
point7 = workPart.Points.CreatePoint(coordinates7)

Dim geometricConstraintData7 As NXOpen.Features.GeometricConstraintData = Nothing
geometricConstraintData7 = studioSplineBuilderEx1.ConstraintManager.CreateGeometricConstraintData()

geometricConstraintData7.Point = point7

studioSplineBuilderEx1.ConstraintManager.Append(geometricConstraintData7)

theSession.SetUndoMarkName(markId13, "艺术样条 - 选择")

theSession.SetUndoMarkVisibility(markId13, Nothing, NXOpen.Session.MarkVisibility.Visible)

theSession.SetUndoMarkVisibility(markId5, Nothing, NXOpen.Session.MarkVisibility.Invisible)

Dim markId14 As NXOpen.Session.UndoMarkId = Nothing
markId14 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

Dim coordinates8 As NXOpen.Point3d = New NXOpen.Point3d(101.09813595496702, 141.79268628355061, 27.379750275887712)
Dim point8 As NXOpen.Point = Nothing
point8 = workPart.Points.CreatePoint(coordinates8)

Dim geometricConstraintData8 As NXOpen.Features.GeometricConstraintData = Nothing
geometricConstraintData8 = studioSplineBuilderEx1.ConstraintManager.CreateGeometricConstraintData()

geometricConstraintData8.Point = point8

studioSplineBuilderEx1.ConstraintManager.Append(geometricConstraintData8)

theSession.SetUndoMarkName(markId14, "艺术样条 - 选择")

theSession.SetUndoMarkVisibility(markId14, Nothing, NXOpen.Session.MarkVisibility.Visible)

theSession.SetUndoMarkVisibility(markId5, Nothing, NXOpen.Session.MarkVisibility.Invisible)

Dim markId15 As NXOpen.Session.UndoMarkId = Nothing
markId15 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

Dim markId16 As NXOpen.Session.UndoMarkId = Nothing
markId16 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

Dim nXObject2 As NXOpen.NXObject = Nothing
nXObject2 = studioSplineBuilderEx1.Commit()

theSession.DeleteUndoMark(markId16, Nothing)

theSession.SetUndoMarkName(markId5, "艺术样条")

studioSplineBuilderEx1.Destroy()

Try
  ' 表达式仍然在使用中。
  workPart.Expressions.Delete(expression2)
Catch ex As NXException
  ex.AssertErrorCode(1050029)
End Try

Try
  ' 表达式仍然在使用中。
  workPart.Expressions.Delete(expression4)
Catch ex As NXException
  ex.AssertErrorCode(1050029)
End Try

Try
  ' 表达式仍然在使用中。
  workPart.Expressions.Delete(expression1)
Catch ex As NXException
  ex.AssertErrorCode(1050029)
End Try

Try
  ' 表达式仍然在使用中。
  workPart.Expressions.Delete(expression3)
Catch ex As NXException
  ex.AssertErrorCode(1050029)
End Try

theSession.SetUndoMarkVisibility(markId5, Nothing, NXOpen.Session.MarkVisibility.Visible)

theSession.DeleteUndoMark(markId14, Nothing)

theSession.DeleteUndoMark(markId13, Nothing)

theSession.DeleteUndoMark(markId12, Nothing)

theSession.DeleteUndoMark(markId11, Nothing)

theSession.DeleteUndoMark(markId10, Nothing)

theSession.DeleteUndoMark(markId9, Nothing)

theSession.DeleteUndoMark(markId8, Nothing)

theSession.DeleteUndoMark(markId7, Nothing)

Dim markId17 As NXOpen.Session.UndoMarkId = Nothing
markId17 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "Start")

Dim studioSplineBuilderEx2 As NXOpen.Features.StudioSplineBuilderEx = Nothing
studioSplineBuilderEx2 = workPart.Features.CreateStudioSplineBuilderEx(nullNXOpen_NXObject)

Dim origin3 As NXOpen.Point3d = New NXOpen.Point3d(0.0, 0.0, 0.0)
Dim normal3 As NXOpen.Vector3d = New NXOpen.Vector3d(0.0, 0.0, 1.0)
Dim plane3 As NXOpen.Plane = Nothing
plane3 = workPart.Planes.CreatePlane(origin3, normal3, NXOpen.SmartObject.UpdateOption.WithinModeling)

studioSplineBuilderEx2.DrawingPlane = plane3

Dim expression5 As NXOpen.Expression = Nothing
expression5 = workPart.Expressions.CreateSystemExpressionWithUnits("0", unit1)

Dim expression6 As NXOpen.Expression = Nothing
expression6 = workPart.Expressions.CreateSystemExpressionWithUnits("0", unit1)

Dim origin4 As NXOpen.Point3d = New NXOpen.Point3d(0.0, 0.0, 0.0)
Dim normal4 As NXOpen.Vector3d = New NXOpen.Vector3d(0.0, 0.0, 1.0)
Dim plane4 As NXOpen.Plane = Nothing
plane4 = workPart.Planes.CreatePlane(origin4, normal4, NXOpen.SmartObject.UpdateOption.WithinModeling)

studioSplineBuilderEx2.MovementPlane = plane4

Dim expression7 As NXOpen.Expression = Nothing
expression7 = workPart.Expressions.CreateSystemExpressionWithUnits("0", unit1)

Dim expression8 As NXOpen.Expression = Nothing
expression8 = workPart.Expressions.CreateSystemExpressionWithUnits("0", unit1)

studioSplineBuilderEx2.OrientExpress.ReferenceOption = NXOpen.GeometricUtilities.OrientXpressBuilder.Reference.WcsDisplayPart

studioSplineBuilderEx2.MovementMethod = NXOpen.Features.StudioSplineBuilderEx.MovementMethodType.View

studioSplineBuilderEx2.OrientExpress.AxisOption = NXOpen.GeometricUtilities.OrientXpressBuilder.Axis.Passive

studioSplineBuilderEx2.OrientExpress.PlaneOption = NXOpen.GeometricUtilities.OrientXpressBuilder.Plane.Passive

studioSplineBuilderEx2.Extender.StartValue.RightHandSide = "0"

studioSplineBuilderEx2.Extender.EndValue.RightHandSide = "0"

studioSplineBuilderEx2.InputCurveOption = NXOpen.Features.StudioSplineBuilderEx.InputCurveOptions.Hide

theSession.SetUndoMarkName(markId17, "艺术样条 对话框")

studioSplineBuilderEx2.MatchKnotsType = NXOpen.Features.StudioSplineBuilderEx.MatchKnotsTypes.None

Dim markId18 As NXOpen.Session.UndoMarkId = Nothing
markId18 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

' ----------------------------------------------
'   对话开始 艺术样条
' ----------------------------------------------
theSession.DeleteUndoMark(markId18, Nothing)

Dim markId19 As NXOpen.Session.UndoMarkId = Nothing
markId19 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "艺术样条")

studioSplineBuilderEx2.Destroy()

Try
  ' 表达式仍然在使用中。
  workPart.Expressions.Delete(expression6)
Catch ex As NXException
  ex.AssertErrorCode(1050029)
End Try

Try
  ' 表达式仍然在使用中。
  workPart.Expressions.Delete(expression8)
Catch ex As NXException
  ex.AssertErrorCode(1050029)
End Try

Try
  ' 表达式仍然在使用中。
  workPart.Expressions.Delete(expression5)
Catch ex As NXException
  ex.AssertErrorCode(1050029)
End Try

Try
  ' 表达式仍然在使用中。
  workPart.Expressions.Delete(expression7)
Catch ex As NXException
  ex.AssertErrorCode(1050029)
End Try

theSession.UndoToMark(markId17, Nothing)

theSession.DeleteUndoMark(markId17, Nothing)

' ----------------------------------------------
'   菜单：插入(S)->设计特征(E)->旋转(R)...
' ----------------------------------------------
Dim markId20 As NXOpen.Session.UndoMarkId = Nothing
markId20 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "开始")

Dim nullNXOpen_Features_Feature As NXOpen.Features.Feature = Nothing

Dim revolveBuilder1 As NXOpen.Features.RevolveBuilder = Nothing
revolveBuilder1 = workPart.Features.CreateRevolveBuilder(nullNXOpen_Features_Feature)

revolveBuilder1.Limits.StartExtend.Value.RightHandSide = "0"

revolveBuilder1.Limits.EndExtend.Value.RightHandSide = "360"

revolveBuilder1.Tolerance = 0.001

Dim section1 As NXOpen.Section = Nothing
section1 = workPart.Sections.CreateSection(0.00095, 0.001, 0.050000000000000003)

revolveBuilder1.Section = section1

Dim smartVolumeProfileBuilder1 As NXOpen.GeometricUtilities.SmartVolumeProfileBuilder = Nothing
smartVolumeProfileBuilder1 = revolveBuilder1.SmartVolumeProfile

smartVolumeProfileBuilder1.OpenProfileSmartVolumeOption = False

smartVolumeProfileBuilder1.CloseProfileRule = NXOpen.GeometricUtilities.SmartVolumeProfileBuilder.CloseProfileRuleType.Fci

theSession.SetUndoMarkName(markId20, "旋转 对话框")

section1.DistanceTolerance = 0.001

section1.ChainingTolerance = 0.00095

Dim starthelperpoint1(2) As Double
starthelperpoint1(0) = 0.0
starthelperpoint1(1) = 0.0
starthelperpoint1(2) = 0.0
revolveBuilder1.SetStartLimitHelperPoint(starthelperpoint1)

Dim endhelperpoint1(2) As Double
endhelperpoint1(0) = 0.0
endhelperpoint1(1) = 0.0
endhelperpoint1(2) = 0.0
revolveBuilder1.SetEndLimitHelperPoint(endhelperpoint1)

section1.SetAllowedEntityTypes(NXOpen.Section.AllowTypes.OnlyCurves)

Dim markId21 As NXOpen.Session.UndoMarkId = Nothing
markId21 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "section mark")

Dim markId22 As NXOpen.Session.UndoMarkId = Nothing
markId22 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, Nothing)

Dim features1(0) As NXOpen.Features.Feature
Dim studioSpline1 As NXOpen.Features.StudioSpline = CType(nXObject2, NXOpen.Features.StudioSpline)

features1(0) = studioSpline1
Dim curveFeatureRule1 As NXOpen.CurveFeatureRule = Nothing
curveFeatureRule1 = workPart.ScRuleFactory.CreateRuleCurveFeature(features1)

section1.AllowSelfIntersection(False)

Dim rules1(0) As NXOpen.SelectionIntentRule
rules1(0) = curveFeatureRule1
Dim spline1 As NXOpen.Spline = CType(studioSpline1.FindObject("CURVE 1"), NXOpen.Spline)

Dim helpPoint1 As NXOpen.Point3d = New NXOpen.Point3d(-42.063572720025221, -43.188716348122377, 13.240856222131708)
section1.AddToSection(rules1, spline1, nullNXOpen_NXObject, nullNXOpen_NXObject, helpPoint1, NXOpen.Section.Mode.Create, False)

theSession.DeleteUndoMark(markId22, Nothing)

revolveBuilder1.Section = section1

theSession.DeleteUndoMark(markId21, Nothing)

Dim expression9 As NXOpen.Expression = Nothing
expression9 = workPart.Expressions.CreateSystemExpressionWithUnits("0", unit1)

Dim scalar1 As NXOpen.Scalar = Nothing
scalar1 = workPart.Scalars.CreateScalar(0.0, NXOpen.Scalar.DimensionalityType.None, NXOpen.SmartObject.UpdateOption.WithinModeling)

Dim point9 As NXOpen.Point = Nothing
point9 = workPart.Points.CreatePoint(spline1, scalar1, NXOpen.SmartObject.UpdateOption.WithinModeling)

Dim scalar2 As NXOpen.Scalar = Nothing
scalar2 = workPart.Scalars.CreateScalar(248.16442699836364, NXOpen.Scalar.DimensionalityType.None, NXOpen.SmartObject.UpdateOption.WithinModeling)

Dim point10 As NXOpen.Point = Nothing
point10 = workPart.Points.CreatePoint(spline1, point9, scalar2, NXOpen.PointCollection.AlongCurveOption.Distance, NXOpen.Sense.Forward, NXOpen.SmartObject.UpdateOption.WithinModeling)

Dim direction1 As NXOpen.Direction = Nothing
direction1 = workPart.Directions.CreateDirection(spline1, point10, NXOpen.Direction.OnCurveOption.Tangent, NXOpen.Sense.Forward, NXOpen.SmartObject.UpdateOption.WithinModeling)

Dim nullNXOpen_Point As NXOpen.Point = Nothing

Dim axis1 As NXOpen.Axis = Nothing
axis1 = workPart.Axes.CreateAxis(nullNXOpen_Point, direction1, NXOpen.SmartObject.UpdateOption.WithinModeling)

axis1.Point = nullNXOpen_Point

axis1.Evaluate()

revolveBuilder1.Axis = axis1

Dim expression10 As NXOpen.Expression = Nothing
expression10 = workPart.Expressions.CreateSystemExpressionWithUnits("0", unit1)

Dim scalar3 As NXOpen.Scalar = Nothing
scalar3 = workPart.Scalars.CreateScalar(0.0, NXOpen.Scalar.DimensionalityType.None, NXOpen.SmartObject.UpdateOption.WithinModeling)

Dim point11 As NXOpen.Point = Nothing
point11 = workPart.Points.CreatePoint(spline1, scalar3, NXOpen.SmartObject.UpdateOption.WithinModeling)

Dim nXObject3 As NXOpen.NXObject = Nothing
Dim xform1 As NXOpen.Xform = Nothing
xform1 = workPart.Xforms.CreateExtractXform(spline1, NXOpen.SmartObject.UpdateOption.WithinModeling, False, nXObject3)

Dim scalar4 As NXOpen.Scalar = Nothing
scalar4 = workPart.Scalars.CreateScalar(0.0, NXOpen.Scalar.DimensionalityType.None, NXOpen.SmartObject.UpdateOption.WithinModeling)

Dim spline2 As NXOpen.Spline = CType(nXObject3, NXOpen.Spline)

Dim point12 As NXOpen.Point = Nothing
point12 = workPart.Points.CreatePoint(spline2, scalar4, NXOpen.SmartObject.UpdateOption.WithinModeling)

point12.RemoveViewDependency()

point12.RemoveViewDependency()

Dim point13 As NXOpen.Point = Nothing
point13 = axis1.Point

axis1.Point = point12

revolveBuilder1.Axis = axis1

Dim scaleAboutPoint2 As NXOpen.Point3d = New NXOpen.Point3d(-58.759833018532788, 12.955954273574061, 0.0)
Dim viewCenter2 As NXOpen.Point3d = New NXOpen.Point3d(58.759833018532788, -12.955954273574061, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint2, viewCenter2)

Dim scaleAboutPoint3 As NXOpen.Point3d = New NXOpen.Point3d(-73.449791273165999, 16.194942841967571, 0.0)
Dim viewCenter3 As NXOpen.Point3d = New NXOpen.Point3d(73.449791273165999, -16.194942841967571, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint3, viewCenter3)

Dim scaleAboutPoint4 As NXOpen.Point3d = New NXOpen.Point3d(-68.910299718978109, -43.96354433109876, 0.0)
Dim viewCenter4 As NXOpen.Point3d = New NXOpen.Point3d(68.910299718978109, 43.96354433109876, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint4, viewCenter4)

Dim scaleAboutPoint5 As NXOpen.Point3d = New NXOpen.Point3d(-106.49401808202911, -45.313122901262737, 0.0)
Dim viewCenter5 As NXOpen.Point3d = New NXOpen.Point3d(106.49401808202911, 45.313122901262737, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint5, viewCenter5)

Dim scaleAboutPoint6 As NXOpen.Point3d = New NXOpen.Point3d(-133.11752260253638, -56.641403626578416, 0.0)
Dim viewCenter6 As NXOpen.Point3d = New NXOpen.Point3d(133.11752260253638, 56.641403626578416, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint6, viewCenter6)

Dim markId23 As NXOpen.Session.UndoMarkId = Nothing
markId23 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "旋转")

theSession.DeleteUndoMark(markId23, Nothing)

Dim markId24 As NXOpen.Session.UndoMarkId = Nothing
markId24 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "旋转")

revolveBuilder1.ParentFeatureInternal = False

Dim feature1 As NXOpen.Features.Feature = Nothing
feature1 = revolveBuilder1.CommitFeature()

theSession.DeleteUndoMark(markId24, Nothing)

theSession.SetUndoMarkName(markId20, "旋转")

Dim expression11 As NXOpen.Expression = revolveBuilder1.Limits.StartExtend.Value

Dim expression12 As NXOpen.Expression = revolveBuilder1.Limits.EndExtend.Value

revolveBuilder1.Destroy()

workPart.Expressions.Delete(expression10)

workPart.Expressions.Delete(expression9)

workPart.Points.DeletePoint(point11)

Dim rotMatrix1 As NXOpen.Matrix3x3 = Nothing
rotMatrix1.Xx = 0.11035872623074271
rotMatrix1.Xy = 0.91551544637985593
rotMatrix1.Xz = -0.38684934921054076
rotMatrix1.Yx = -0.77046877973378436
rotMatrix1.Yy = 0.32468308164634513
rotMatrix1.Yz = 0.54859707978457584
rotMatrix1.Zx = 0.62785253921622253
rotMatrix1.Zy = 0.23751287108812402
rotMatrix1.Zz = 0.74120768011888138
Dim translation1 As NXOpen.Point3d = New NXOpen.Point3d(-16.78470811454401, 18.441750689133144, -1.0059492185867818)
workPart.ModelingViews.WorkView.SetRotationTranslationScale(rotMatrix1, translation1, 0.82759302680381142)

Dim scaleAboutPoint7 As NXOpen.Point3d = New NXOpen.Point3d(-112.0556304002273, -76.888385481468362, 0.0)
Dim viewCenter7 As NXOpen.Point3d = New NXOpen.Point3d(112.0556304002273, 76.888385481468362, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint7, viewCenter7)

Dim scaleAboutPoint8 As NXOpen.Point3d = New NXOpen.Point3d(-138.87065465078101, -96.110481851835416, 0.0)
Dim viewCenter8 As NXOpen.Point3d = New NXOpen.Point3d(138.87065465078101, 96.110481851835445, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint8, viewCenter8)

Dim rotMatrix2 As NXOpen.Matrix3x3 = Nothing
rotMatrix2.Xx = 0.50225187334137711
rotMatrix2.Xy = 0.83830933695633958
rotMatrix2.Xz = 0.21208609406770634
rotMatrix2.Yx = -0.77440762944368746
rotMatrix2.Yy = 0.3269270550057744
rotMatrix2.Yz = 0.54167474019438822
rotMatrix2.Zx = 0.38475431015712114
rotMatrix2.Zy = -0.43629824234927894
rotMatrix2.Zz = 0.81339287219549805
Dim translation2 As NXOpen.Point3d = New NXOpen.Point3d(-100.60180247469404, -24.487374876135988, -41.348614310632378)
workPart.ModelingViews.WorkView.SetRotationTranslationScale(rotMatrix2, translation2, 0.52965953715443936)

Dim scaleAboutPoint9 As NXOpen.Point3d = New NXOpen.Point3d(-94.661831137852516, -123.13531068855208, 0.0)
Dim viewCenter9 As NXOpen.Point3d = New NXOpen.Point3d(94.661831137852516, 123.13531068855214, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint9, viewCenter9)

Dim rotMatrix3 As NXOpen.Matrix3x3 = Nothing
rotMatrix3.Xx = 0.34156633401854963
rotMatrix3.Xy = 0.93740738672460244
rotMatrix3.Xz = -0.067822052308047845
rotMatrix3.Yx = -0.76316139926153248
rotMatrix3.Yy = 0.31874592527932499
rotMatrix3.Yz = 0.5621260657494942
rotMatrix3.Zx = 0.54855912912128657
rotMatrix3.Zy = -0.14024416719412594
rotMatrix3.Zz = 0.82426601011185407
Dim translation3 As NXOpen.Point3d = New NXOpen.Point3d(-111.09668746383036, -56.291414409867627, -23.395293107044814)
workPart.ModelingViews.WorkView.SetRotationTranslationScale(rotMatrix3, translation3, 0.42372762972355149)

' ----------------------------------------------
'   菜单：插入(S)->偏置/缩放(O)->抽壳(H)...
' ----------------------------------------------
Dim markId25 As NXOpen.Session.UndoMarkId = Nothing
markId25 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "开始")

Dim shellBuilder1 As NXOpen.Features.ShellBuilder = Nothing
shellBuilder1 = workPart.Features.CreateShellBuilder(nullNXOpen_Features_Feature)

shellBuilder1.Tolerance = 0.001

shellBuilder1.UseSurfaceApproximation = True

shellBuilder1.TgtPierceOption = False

shellBuilder1.SetDefaultThickness("5")

theSession.SetUndoMarkName(markId25, "抽壳 对话框")

Dim scaleAboutPoint10 As NXOpen.Point3d = New NXOpen.Point3d(-144.09562858521483, 95.531248219466221, 0.0)
Dim viewCenter10 As NXOpen.Point3d = New NXOpen.Point3d(144.09562858521483, -95.531248219466093, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint10, viewCenter10)

Dim scaleAboutPoint11 As NXOpen.Point3d = New NXOpen.Point3d(-112.22525397019221, 129.79789160253549, 0.0)
Dim viewCenter11 As NXOpen.Point3d = New NXOpen.Point3d(112.22525397019221, -129.79789160253549, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint11, viewCenter11)

Dim rotMatrix4 As NXOpen.Matrix3x3 = Nothing
rotMatrix4.Xx = 0.43075680618679579
rotMatrix4.Xy = -0.3103439760054007
rotMatrix4.Xz = 0.84742857544509631
rotMatrix4.Yx = -0.82240916185203816
rotMatrix4.Yy = 0.25166527839370617
rotMatrix4.Yz = 0.51020364380592653
rotMatrix4.Zx = -0.37160697574934687
rotMatrix4.Zy = -0.91670671657197678
rotMatrix4.Zz = -0.14682319764344692
Dim translation4 As NXOpen.Point3d = New NXOpen.Point3d(-222.01590346453042, -60.36862023925859, -34.720181320021901)
workPart.ModelingViews.WorkView.SetRotationTranslationScale(rotMatrix4, translation4, 0.41405518163504207)

Dim scaleAboutPoint12 As NXOpen.Point3d = New NXOpen.Point3d(-84.029158132841388, 197.77204898946337, 0.0)
Dim viewCenter12 As NXOpen.Point3d = New NXOpen.Point3d(84.029158132841388, -197.77204898946329, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint12, viewCenter12)

Dim scaleAboutPoint13 As NXOpen.Point3d = New NXOpen.Point3d(-158.21763919157073, 74.891386564022895, 0.0)
Dim viewCenter13 As NXOpen.Point3d = New NXOpen.Point3d(158.21763919157061, -74.891386564022895, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint13, viewCenter13)

Dim scaleAboutPoint14 As NXOpen.Point3d = New NXOpen.Point3d(-95.492907919177412, 79.952306202137819, 0.0)
Dim viewCenter14 As NXOpen.Point3d = New NXOpen.Point3d(95.492907919177327, -79.952306202137819, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint14, viewCenter14)

Dim scaleAboutPoint15 As NXOpen.Point3d = New NXOpen.Point3d(-97.006071770573399, 30.590447590383182, 0.0)
Dim viewCenter15 As NXOpen.Point3d = New NXOpen.Point3d(97.006071770573271, -30.590447590383182, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint15, viewCenter15)

Dim scaleAboutPoint16 As NXOpen.Point3d = New NXOpen.Point3d(-71.323182617150096, 25.257567422220141, 0.0)
Dim viewCenter16 As NXOpen.Point3d = New NXOpen.Point3d(71.323182617149982, -25.257567422220117, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint16, viewCenter16)

Dim scaleAboutPoint17 As NXOpen.Point3d = New NXOpen.Point3d(-58.727115962286398, 35.170835464879055, 0.0)
Dim viewCenter17 As NXOpen.Point3d = New NXOpen.Point3d(58.727115962286398, -35.170835464879055, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint17, viewCenter17)

Dim scaleAboutPoint18 As NXOpen.Point3d = New NXOpen.Point3d(-73.408894952857892, 43.963544331098809, 0.0)
Dim viewCenter18 As NXOpen.Point3d = New NXOpen.Point3d(73.408894952857978, -43.963544331098809, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint18, viewCenter18)

Dim scaleAboutPoint19 As NXOpen.Point3d = New NXOpen.Point3d(-123.45576692977147, 51.887206390773635, 0.0)
Dim viewCenter19 As NXOpen.Point3d = New NXOpen.Point3d(123.45576692977168, -51.887206390773478, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint19, viewCenter19)

Dim scaleAboutPoint20 As NXOpen.Point3d = New NXOpen.Point3d(-98.764613543817163, 41.509765112618943, 0.0)
Dim viewCenter20 As NXOpen.Point3d = New NXOpen.Point3d(98.764613543817248, -41.509765112618823, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint20, viewCenter20)

Dim scaleAboutPoint21 As NXOpen.Point3d = New NXOpen.Point3d(-127.03419495672149, 50.353594379223686, 0.0)
Dim viewCenter21 As NXOpen.Point3d = New NXOpen.Point3d(127.03419495672159, -50.35359437922353, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint21, viewCenter21)

Dim scaleAboutPoint22 As NXOpen.Point3d = New NXOpen.Point3d(-21.406667661217966, 163.26577872958927, 0.0)
Dim viewCenter22 As NXOpen.Point3d = New NXOpen.Point3d(21.406667661218226, -163.26577872958921, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint22, viewCenter22)

Dim scaleAboutPoint23 As NXOpen.Point3d = New NXOpen.Point3d(-5.3676420404246992, 123.96697093362151, 0.0)
Dim viewCenter23 As NXOpen.Point3d = New NXOpen.Point3d(5.367642040424804, -123.96697093362162, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint23, viewCenter23)

Dim rotMatrix5 As NXOpen.Matrix3x3 = Nothing
rotMatrix5.Xx = 0.45201451226386163
rotMatrix5.Xy = -0.25549264725410326
rotMatrix5.Xz = 0.85463816197379594
rotMatrix5.Yx = -0.77390986215433466
rotMatrix5.Yy = 0.36410001596488717
rotMatrix5.Yz = 0.51816474565009363
rotMatrix5.Zx = -0.44356105099875315
rotMatrix5.Zy = -0.89563088690233117
rotMatrix5.Zz = -0.033149788286235993
Dim translation5 As NXOpen.Point3d = New NXOpen.Point3d(-212.24585730269536, -94.14331931936178, -45.262214919687494)
workPart.ModelingViews.WorkView.SetRotationTranslationScale(rotMatrix5, translation5, 0.41405518163504224)

Dim scaleAboutPoint24 As NXOpen.Point3d = New NXOpen.Point3d(-34.186767757467656, 106.39433330127828, 0.0)
Dim viewCenter24 As NXOpen.Point3d = New NXOpen.Point3d(34.186767757467919, -106.39433330127828, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint24, viewCenter24)

Dim expression13 As NXOpen.Expression = shellBuilder1.DefaultThickness

shellBuilder1.Destroy()

theSession.UndoToMark(markId25, Nothing)

theSession.DeleteUndoMark(markId25, Nothing)

' ----------------------------------------------
'   菜单：插入(S)->设计特征(E)->长方体(K)...
' ----------------------------------------------
Dim markId26 As NXOpen.Session.UndoMarkId = Nothing
markId26 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "开始")

Dim blockFeatureBuilder1 As NXOpen.Features.BlockFeatureBuilder = Nothing
blockFeatureBuilder1 = workPart.Features.CreateBlockFeatureBuilder(nullNXOpen_Features_Feature)

blockFeatureBuilder1.BooleanOption.Type = NXOpen.GeometricUtilities.BooleanOperation.BooleanType.Create

Dim targetBodies1(0) As NXOpen.Body
Dim nullNXOpen_Body As NXOpen.Body = Nothing

targetBodies1(0) = nullNXOpen_Body
blockFeatureBuilder1.BooleanOption.SetTargetBodies(targetBodies1)

blockFeatureBuilder1.BooleanOption.Type = NXOpen.GeometricUtilities.BooleanOperation.BooleanType.Create

Dim targetBodies2(0) As NXOpen.Body
targetBodies2(0) = nullNXOpen_Body
blockFeatureBuilder1.BooleanOption.SetTargetBodies(targetBodies2)

theSession.SetUndoMarkName(markId26, "长方体 对话框")

Dim expression14 As NXOpen.Expression = Nothing
expression14 = workPart.Expressions.CreateSystemExpressionWithUnits("0", unit1)

Dim scalar5 As NXOpen.Scalar = Nothing
scalar5 = workPart.Scalars.CreateScalar(0.0, NXOpen.Scalar.DimensionalityType.None, NXOpen.SmartObject.UpdateOption.WithinModeling)

Dim point14 As NXOpen.Point = Nothing
point14 = workPart.Points.CreatePoint(spline2, scalar5, NXOpen.SmartObject.UpdateOption.WithinModeling)

Dim nXObject4 As NXOpen.NXObject = Nothing
Dim xform2 As NXOpen.Xform = Nothing
xform2 = workPart.Xforms.CreateExtractXform(spline2, NXOpen.SmartObject.UpdateOption.WithinModeling, False, nXObject4)

Dim scalar6 As NXOpen.Scalar = Nothing
scalar6 = workPart.Scalars.CreateScalar(0.0, NXOpen.Scalar.DimensionalityType.None, NXOpen.SmartObject.UpdateOption.WithinModeling)

Dim spline3 As NXOpen.Spline = CType(nXObject4, NXOpen.Spline)

Dim point15 As NXOpen.Point = Nothing
point15 = workPart.Points.CreatePoint(spline3, scalar6, NXOpen.SmartObject.UpdateOption.WithinModeling)

point15.RemoveViewDependency()

point15.RemoveViewDependency()

Dim markId27 As NXOpen.Session.UndoMarkId = Nothing
markId27 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "长方体")

blockFeatureBuilder1.Type = NXOpen.Features.BlockFeatureBuilder.Types.OriginAndEdgeLengths

blockFeatureBuilder1.OriginPoint = point15

Dim originPoint1 As NXOpen.Point3d = New NXOpen.Point3d(-71.741900926500819, -63.129281379192406, 38.995401908082478)
blockFeatureBuilder1.SetOriginAndLengths(originPoint1, "30", "20", "50")

blockFeatureBuilder1.SetBooleanOperationAndTarget(NXOpen.Features.Feature.BooleanType.Create, nullNXOpen_Body)

Dim feature2 As NXOpen.Features.Feature = Nothing
feature2 = blockFeatureBuilder1.CommitFeature()

theSession.DeleteUndoMark(markId27, Nothing)

theSession.SetUndoMarkName(markId26, "长方体")

blockFeatureBuilder1.Destroy()

workPart.Expressions.Delete(expression14)

workPart.Points.DeletePoint(point14)

Dim markId28 As NXOpen.Session.UndoMarkId = Nothing
markId28 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "Start")

Dim blockFeatureBuilder2 As NXOpen.Features.BlockFeatureBuilder = Nothing
blockFeatureBuilder2 = workPart.Features.CreateBlockFeatureBuilder(nullNXOpen_Features_Feature)

blockFeatureBuilder2.BooleanOption.Type = NXOpen.GeometricUtilities.BooleanOperation.BooleanType.Create

Dim targetBodies3(0) As NXOpen.Body
targetBodies3(0) = nullNXOpen_Body
blockFeatureBuilder2.BooleanOption.SetTargetBodies(targetBodies3)

blockFeatureBuilder2.BooleanOption.Type = NXOpen.GeometricUtilities.BooleanOperation.BooleanType.Create

Dim targetBodies4(0) As NXOpen.Body
targetBodies4(0) = nullNXOpen_Body
blockFeatureBuilder2.BooleanOption.SetTargetBodies(targetBodies4)

theSession.SetUndoMarkName(markId28, "长方体 对话框")

' ----------------------------------------------
'   对话开始 长方体
' ----------------------------------------------
Dim expression15 As NXOpen.Expression = Nothing
expression15 = workPart.Expressions.CreateSystemExpressionWithUnits("0", unit1)

blockFeatureBuilder2.Destroy()

workPart.Expressions.Delete(expression15)

theSession.UndoToMark(markId28, Nothing)

theSession.DeleteUndoMark(markId28, Nothing)

Dim scaleAboutPoint25 As NXOpen.Point3d = New NXOpen.Point3d(-228.53713849903687, -55.698122279000174, 0.0)
Dim viewCenter25 As NXOpen.Point3d = New NXOpen.Point3d(228.53713849903718, 55.698122279000174, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint25, viewCenter25)

Dim scaleAboutPoint26 As NXOpen.Point3d = New NXOpen.Point3d(-182.82971079922945, -44.558497823200184, 0.0)
Dim viewCenter26 As NXOpen.Point3d = New NXOpen.Point3d(182.82971079922964, 44.558497823200106, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint26, viewCenter26)

Dim scaleAboutPoint27 As NXOpen.Point3d = New NXOpen.Point3d(-146.26376863938358, -35.646798258560146, 0.0)
Dim viewCenter27 As NXOpen.Point3d = New NXOpen.Point3d(146.2637686393837, 35.646798258560082, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint27, viewCenter27)

Dim scaleAboutPoint28 As NXOpen.Point3d = New NXOpen.Point3d(-250.76643393774094, -71.733187078604757, 0.0)
Dim viewCenter28 As NXOpen.Point3d = New NXOpen.Point3d(250.76643393774103, 71.733187078604715, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint28, viewCenter28)

Dim scaleAboutPoint29 As NXOpen.Point3d = New NXOpen.Point3d(-200.61314715019276, -57.386549662883773, 0.0)
Dim viewCenter29 As NXOpen.Point3d = New NXOpen.Point3d(200.6131471501929, 57.386549662883773, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint29, viewCenter29)

Dim scaleAboutPoint30 As NXOpen.Point3d = New NXOpen.Point3d(-250.76643393774094, -71.733187078604715, 0.0)
Dim viewCenter30 As NXOpen.Point3d = New NXOpen.Point3d(250.76643393774103, 71.733187078604715, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint30, viewCenter30)

Dim scaleAboutPoint31 As NXOpen.Point3d = New NXOpen.Point3d(-311.95943823529723, -89.666483848255893, 0.0)
Dim viewCenter31 As NXOpen.Point3d = New NXOpen.Point3d(311.95943823529734, 89.666483848255893, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint31, viewCenter31)

Dim scaleAboutPoint32 As NXOpen.Point3d = New NXOpen.Point3d(-463.00625190446931, -162.66099611748385, 0.0)
Dim viewCenter32 As NXOpen.Point3d = New NXOpen.Point3d(463.00625190446942, 162.66099611748371, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint32, viewCenter32)

Dim scaleAboutPoint33 As NXOpen.Point3d = New NXOpen.Point3d(-331.94082739368287, -86.169740745538462, 0.0)
Dim viewCenter33 As NXOpen.Point3d = New NXOpen.Point3d(331.94082739368292, 86.16974074553832, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint33, viewCenter33)

Dim scaleAboutPoint34 As NXOpen.Point3d = New NXOpen.Point3d(-234.38169482786458, -43.759242256864781, 0.0)
Dim viewCenter34 As NXOpen.Point3d = New NXOpen.Point3d(234.38169482786466, 43.75924225686466, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint34, viewCenter34)

Dim scaleAboutPoint35 As NXOpen.Point3d = New NXOpen.Point3d(-292.97711853483065, -54.699052821080969, 0.0)
Dim viewCenter35 As NXOpen.Point3d = New NXOpen.Point3d(292.97711853483071, 54.699052821080812, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint35, viewCenter35)

Dim scaleAboutPoint36 As NXOpen.Point3d = New NXOpen.Point3d(-366.22139816853843, -68.37381602635115, 0.0)
Dim viewCenter36 As NXOpen.Point3d = New NXOpen.Point3d(366.2213981685386, 68.373816026351022, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint36, viewCenter36)

Dim scaleAboutPoint37 As NXOpen.Point3d = New NXOpen.Point3d(-457.77674771067302, -85.467270032938856, 0.0)
Dim viewCenter37 As NXOpen.Point3d = New NXOpen.Point3d(457.77674771067313, 85.467270032938771, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint37, viewCenter37)

Dim scaleAboutPoint38 As NXOpen.Point3d = New NXOpen.Point3d(-572.22093463834119, -106.83408754117355, 0.0)
Dim viewCenter38 As NXOpen.Point3d = New NXOpen.Point3d(572.22093463834142, 106.83408754117345, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(0.80000000000000004, scaleAboutPoint38, viewCenter38)

Dim scaleAboutPoint39 As NXOpen.Point3d = New NXOpen.Point3d(-715.27616829792646, -133.54260942646695, 0.0)
Dim viewCenter39 As NXOpen.Point3d = New NXOpen.Point3d(715.2761682979268, 133.54260942646695, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint39, viewCenter39)

Dim scaleAboutPoint40 As NXOpen.Point3d = New NXOpen.Point3d(-572.22093463834108, -106.83408754117355, 0.0)
Dim viewCenter40 As NXOpen.Point3d = New NXOpen.Point3d(572.22093463834153, 106.83408754117355, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint40, viewCenter40)

Dim scaleAboutPoint41 As NXOpen.Point3d = New NXOpen.Point3d(-457.77674771067291, -85.467270032938856, 0.0)
Dim viewCenter41 As NXOpen.Point3d = New NXOpen.Point3d(457.77674771067342, 85.467270032938856, 0.0)
workPart.ModelingViews.WorkView.ZoomAboutPoint(1.25, scaleAboutPoint41, viewCenter41)

Dim rotMatrix6 As NXOpen.Matrix3x3 = Nothing
rotMatrix6.Xx = 0.48036541370498032
rotMatrix6.Xy = -0.1956884023229275
rotMatrix6.Xz = 0.85495913265625612
rotMatrix6.Yx = -0.77390986215433466
rotMatrix6.Yy = 0.36410001596488717
rotMatrix6.Yz = 0.51816474565009363
rotMatrix6.Zx = -0.41268946506580262
rotMatrix6.Zy = -0.91056972691313764
rotMatrix6.Zz = 0.023455870332024585
Dim translation6 As NXOpen.Point3d = New NXOpen.Point3d(-269.73418986190933, -119.48090565241436, -47.839424623272095)
workPart.ModelingViews.WorkView.SetRotationTranslationScale(rotMatrix6, translation6, 0.42372762972355199)

Dim rotMatrix7 As NXOpen.Matrix3x3 = Nothing
rotMatrix7.Xx = 0.63538326431993364
rotMatrix7.Xy = 0.47208542843187218
rotMatrix7.Xz = 0.61108383687055223
rotMatrix7.Yx = -0.77202632071051369
rotMatrix7.Yy = 0.37172362180761198
rotMatrix7.Yz = 0.51555495257093298
rotMatrix7.Zx = 0.016231683595007276
rotMatrix7.Zy = -0.79934779492566532
rotMatrix7.Zz = 0.60064934462225439
Dim translation7 As NXOpen.Point3d = New NXOpen.Point3d(-223.01391164234576, -118.95292379278457, -59.179980732055647)
workPart.ModelingViews.WorkView.SetRotationTranslationScale(rotMatrix7, translation7, 0.42372762972355199)

Dim rotMatrix8 As NXOpen.Matrix3x3 = Nothing
rotMatrix8.Xx = 0.6240283048544284
rotMatrix8.Xy = 0.59731829254636171
rotMatrix8.Xz = 0.50378520435797103
rotMatrix8.Yx = -0.77202632071051369
rotMatrix8.Yy = 0.37172362180761198
rotMatrix8.Yz = 0.51555495257093298
rotMatrix8.Zx = 0.12068154320645563
rotMatrix8.Zy = -0.71065632086102404
rotMatrix8.Zz = 0.69311150527860721
Dim translation8 As NXOpen.Point3d = New NXOpen.Point3d(-212.36035304229659, -118.95292379278457, -56.712138752396932)
workPart.ModelingViews.WorkView.SetRotationTranslationScale(rotMatrix8, translation8, 0.42372762972355199)

Dim rotMatrix9 As NXOpen.Matrix3x3 = Nothing
rotMatrix9.Xx = 0.61599555511122861
rotMatrix9.Xy = 0.63745637700974822
rotMatrix9.Xz = 0.46281620919411454
rotMatrix9.Yx = -0.77202632071051369
rotMatrix9.Yy = 0.37172362180761198
rotMatrix9.Yz = 0.51555495257093298
rotMatrix9.Zx = 0.15660407470239218
rotMatrix9.Zy = -0.67488585434859538
rotMatrix9.Zz = 0.72111320011962687
Dim translation9 As NXOpen.Point3d = New NXOpen.Point3d(-208.74751701445231, -118.95292379278457, -55.436838860239824)
workPart.ModelingViews.WorkView.SetRotationTranslationScale(rotMatrix9, translation9, 0.42372762972355199)

Dim rotMatrix10 As NXOpen.Matrix3x3 = Nothing
rotMatrix10.Xx = 0.58087572868957082
rotMatrix10.Xy = 0.74216267333476627
rotMatrix10.Xz = 0.33433210155165877
rotMatrix10.Yx = -0.77401765796076294
rotMatrix10.Yy = 0.37647567070317095
rotMatrix10.Yz = 0.50908028299427521
rotMatrix10.Zx = 0.25195248159978761
rotMatrix10.Zy = -0.55449133056990763
rotMatrix10.Zz = 0.79313259379407441
Dim translation10 As NXOpen.Point3d = New NXOpen.Point3d(-198.65747087361592, -118.47388898407117, -51.041756553084149)
workPart.ModelingViews.WorkView.SetRotationTranslationScale(rotMatrix10, translation10, 0.42372762972355199)

Dim rotMatrix11 As NXOpen.Matrix3x3 = Nothing
rotMatrix11.Xx = 0.23173663918065987
rotMatrix11.Xy = 0.91169143696043953
rotMatrix11.Xz = -0.33928874699031392
rotMatrix11.Yx = -0.77530453865000215
rotMatrix11.Yy = 0.38375373462888507
rotMatrix11.Yz = 0.5016332759168679
rotMatrix11.Zx = 0.58753808592290879
rotMatrix11.Zy = 0.14680529599230416
rotMatrix11.Zz = 0.79576830965969636
Dim translation11 As NXOpen.Point3d = New NXOpen.Point3d(-167.30089589765231, -117.80861083153692, -9.7753541461140543)
workPart.ModelingViews.WorkView.SetRotationTranslationScale(rotMatrix11, translation11, 0.42372762972355199)

' ----------------------------------------------
'   菜单：插入(S)->偏置/缩放(O)->抽壳(H)...
' ----------------------------------------------
Dim markId29 As NXOpen.Session.UndoMarkId = Nothing
markId29 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "开始")

Dim shellBuilder2 As NXOpen.Features.ShellBuilder = Nothing
shellBuilder2 = workPart.Features.CreateShellBuilder(nullNXOpen_Features_Feature)

shellBuilder2.Tolerance = 0.001

shellBuilder2.UseSurfaceApproximation = True

shellBuilder2.TgtPierceOption = False

shellBuilder2.SetDefaultThickness("5")

theSession.SetUndoMarkName(markId29, "抽壳 对话框")

Dim rotMatrix12 As NXOpen.Matrix3x3 = Nothing
rotMatrix12.Xx = 0.61260950386112212
rotMatrix12.Xy = 0.25682347941029315
rotMatrix12.Xz = 0.74749668641580902
rotMatrix12.Yx = -0.77932835407682466
rotMatrix12.Yy = 0.35391341615248739
rotMatrix12.Yz = 0.51710019377213712
rotMatrix12.Zx = -0.13174563488378785
rotMatrix12.Zy = -0.89932585545555355
rotMatrix12.Zz = 0.41696054177607733
Dim translation12 As NXOpen.Point3d = New NXOpen.Point3d(-240.42002269495694, -120.04190156151142, -58.358540163750696)
workPart.ModelingViews.WorkView.SetRotationTranslationScale(rotMatrix12, translation12, 0.41405518163504257)

Dim scCollector1 As NXOpen.ScCollector = Nothing
scCollector1 = workPart.ScCollectors.CreateCollector()

Dim block1 As NXOpen.Features.Block = CType(feature2, NXOpen.Features.Block)

Dim face1 As NXOpen.Face = CType(block1.FindObject("FACE 3 {(-71.7419009265008,-53.1292813791924,63.9954019080825) BLOCK(3)}"), NXOpen.Face)

Dim boundaryFaces1(-1) As NXOpen.Face
Dim faceTangentRule1 As NXOpen.FaceTangentRule = Nothing
faceTangentRule1 = workPart.ScRuleFactory.CreateRuleFaceTangent(face1, boundaryFaces1, 0.050000000000000003)

Dim rules2(0) As NXOpen.SelectionIntentRule
rules2(0) = faceTangentRule1
scCollector1.ReplaceRules(rules2, False)

shellBuilder2.RemovedFacesCollector = scCollector1

Dim body1 As NXOpen.Body = CType(workPart.Bodies.FindObject("BLOCK(3)"), NXOpen.Body)

shellBuilder2.Body = body1

Dim boundaryFaces2(-1) As NXOpen.Face
Dim faceTangentRule2 As NXOpen.FaceTangentRule = Nothing
faceTangentRule2 = workPart.ScRuleFactory.CreateRuleFaceTangent(face1, boundaryFaces2, 0.050000000000000003)

Dim face2 As NXOpen.Face = CType(block1.FindObject("FACE 2 {(-56.7419009265008,-63.1292813791924,63.9954019080825) BLOCK(3)}"), NXOpen.Face)

Dim boundaryFaces3(-1) As NXOpen.Face
Dim faceTangentRule3 As NXOpen.FaceTangentRule = Nothing
faceTangentRule3 = workPart.ScRuleFactory.CreateRuleFaceTangent(face2, boundaryFaces3, 0.050000000000000003)

Dim rules3(1) As NXOpen.SelectionIntentRule
rules3(0) = faceTangentRule2
rules3(1) = faceTangentRule3
scCollector1.ReplaceRules(rules3, False)

Dim markId30 As NXOpen.Session.UndoMarkId = Nothing
markId30 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Invisible, "抽壳")

Dim nXObject5 As NXOpen.NXObject = Nothing
nXObject5 = shellBuilder2.Commit()

theSession.DeleteUndoMark(markId30, Nothing)

theSession.SetUndoMarkName(markId29, "抽壳")

Dim expression16 As NXOpen.Expression = shellBuilder2.DefaultThickness

shellBuilder2.Destroy()

Dim markId31 As NXOpen.Session.UndoMarkId = Nothing
markId31 = theSession.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, "Start")

Dim shellBuilder3 As NXOpen.Features.ShellBuilder = Nothing
shellBuilder3 = workPart.Features.CreateShellBuilder(nullNXOpen_Features_Feature)

shellBuilder3.Tolerance = 0.001

shellBuilder3.UseSurfaceApproximation = True

shellBuilder3.TgtPierceOption = False

shellBuilder3.SetDefaultThickness("5")

theSession.SetUndoMarkName(markId31, "抽壳 对话框")

' ----------------------------------------------
'   对话开始 抽壳
' ----------------------------------------------
Dim expression17 As NXOpen.Expression = shellBuilder3.DefaultThickness

shellBuilder3.Destroy()

theSession.UndoToMark(markId31, Nothing)

theSession.DeleteUndoMark(markId31, Nothing)

' ----------------------------------------------
'   菜单：工具(T)->操作记录(J)->停止录制(S)
' ----------------------------------------------

End Sub
End Module
