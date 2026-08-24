import math
import NXOpen
import NXOpen.Features

def generate_von_karman_profile(radius, length, num_points=50):
    """
    根据冯·卡门方程生成截面轮廓二维点列 (X方向为轴线，Y方向为半径)
    """
    points = []
    for i in range(num_points + 1):
        x = length * (i / num_points)
        theta = math.acos(1 - 2 * x / length)
        y = radius / math.sqrt(math.pi) * math.sqrt(theta - 0.5 * math.sin(2 * theta))
        points.append((x, y, 0.0))
    return points

def create_fairing(diameter, length, thickness):
    """
    NXOpen 参数化整流罩生成主函数
    1. 根据冯·卡门曲线生成点阵
    2. 创建样条曲线
    3. 将曲线绕X轴旋转360度
    4. 抽壳/加厚获得固体厚度
    """
    # 建立外部独立日志文件
    debug_log = open("d:\\AI_rocket\\cad_automation\\nx_debug.log", "w", encoding="utf-8")
    def log(msg):
        debug_log.write(msg + "\n")
        debug_log.flush()
        try:
            theSession.ListingWindow.WriteLine(msg)
        except:
            pass
            
    try:
        log("NX Session initializing...")
        theSession = NXOpen.Session.GetSession()
        workPart = theSession.Parts.Work

        if workPart is None:
            log("No active part, creating new one...")
            newFile = theSession.Parts.FileNew()
            import os
            out_file = os.path.join(r"d:\AI_rocket\cad_automation", f"fairing_D{diameter}_L{length}.prt")
            newFile.NewFileName = out_file
            newFile.Units = NXOpen.Part.Units.Millimeters
            newFile.UseBlankTemplate = True
            newFile.MakeDisplayedPart = True
            newFile.Commit()
            workPart = theSession.Parts.Work
            newFile.Destroy()

        try:
            theSession.ListingWindow.Open()
        except:
            pass
            
        log("-------------------------------------")
        log(f"Generating Von Karman Fairing: D={diameter}, L={length}, T={thickness}")

        # ---- 1. 生成冯卡门点阵并创建三维点对 ----
        log("Step 1: Calculating points...")
        radius = diameter / 2.0
        # NXOpen SplineBuilder 要求点之间不能过近或重叠，否则会报 Cannot compute bcurve 错误
        # 我们直接使用生成器的方程点，并且确保点阵按正确顺序(从头到尾或从尾到头)连续排列即可
        
        vk_points = generate_von_karman_profile(radius, length, num_points=20)
        
        profile_pts = []
        for p in vk_points:
            profile_pts.append(NXOpen.Point3d(float(p[0]), float(p[1]), float(p[2])))
            
        # 移除原先的尾部点，因为整流罩轮廓线只是单条母线，从(0,0,0)到(L,R,0)，不需要折回X轴
        
        log("Step 1: Successfully calculated Von Karman profile.")

        # ---- 2. 创建样条曲线 (简易 FitSpline/CreateSpline 绕过严格约束) ----
        log("Step 2: Starting Spline creation (basic)...")
        
        # NXOpen 基础的三维过点样条构建方式
        # 不需要通过复杂的 Builder
        pass_through_pts = []
        for p3d in profile_pts:
            pass_through_pts.append(p3d)
        
        # 使用原生点列创建 Spline, 不依赖约束引擎 (不会报 Knot mismatch / bcurve error)
        # 此方法要求输入点列表，并且无自交。
        spline_feature = None
        
        # 针对Python环境最稳定的无UI建线方式之一：NXObjectManager/Splines.CreateSpline
        # 注意: 如果 Python 没有 CreateSpline(points) 直接覆写，可以使用 SplineRoutine
        # 为了兼容性，我们利用一个简单的线段连接(直线段模拟) 或者 尝试基础插值样条
        try:
            # 换用控制极点而不是通过点来避免 G1 约束自纠结
            log("Attempting direct StudioSpline generation without geometry constraints...")
            
            studioSplineBuilder1 = workPart.Features.CreateStudioSplineBuilderEx(NXOpen.NXObject.Null)
            studioSplineBuilder1.Type = NXOpen.Features.StudioSplineBuilderEx.Types.ThroughPoints # 使用 ThroughPoints 精确过点
            studioSplineBuilder1.IsPeriodic = False
            studioSplineBuilder1.Degree = 3
            
            for p3d in pass_through_pts:
                point_obj = workPart.Points.CreatePoint(p3d)
                geometricConstraintData = studioSplineBuilder1.ConstraintManager.CreateGeometricConstraintData()
                geometricConstraintData.Point = point_obj
                studioSplineBuilder1.ConstraintManager.Append(geometricConstraintData)
            
            spline_feature = studioSplineBuilder1.Commit()
            studioSplineBuilder1.Destroy()
            log("Step 2: Studio Spline Created via ByPoles.")
            
        except Exception as bypass_err:
            log("Spline ByPoles failed, Error: " + str(bypass_err))
            raise bypass_err

        # ---- 3. 旋转成型 (RevolveBuilder) ----
        log("Step 3: Starting RevolveBuilder...")
        nullNXOpen_Features_Feature = NXOpen.Features.Feature.Null
        revolveBuilder1 = workPart.Features.CreateRevolveBuilder(nullNXOpen_Features_Feature)
        
        revolveBuilder1.Limits.StartExtend.Value.RightHandSide = "0"
        revolveBuilder1.Limits.EndExtend.Value.RightHandSide = "360"
        
        section1 = workPart.Sections.CreateSection(0.00095, 0.001, 0.05)
        section1.SetAllowedEntityTypes(NXOpen.Section.AllowTypes.OnlyCurves)
        
        features_array = [spline_feature]
        curveFeatureRule1 = workPart.ScRuleFactory.CreateRuleCurveFeature(features_array)
        rules_array = [curveFeatureRule1]
        
        spline_obj = spline_feature.GetEntities()[0]  # 获取真实的样条线实体
        helpPoint = NXOpen.Point3d(float(length / 2.0), float(radius / 2.0), 0.0)
        nullNXOpen_NXObject = NXOpen.NXObject.Null
        section1.AddToSection(rules_array, spline_obj, nullNXOpen_NXObject, nullNXOpen_NXObject, helpPoint, NXOpen.Section.Mode.Create, False)
        revolveBuilder1.Section = section1
        
        origin_pt = NXOpen.Point3d(0.0, 0.0, 0.0)
        vector_x = NXOpen.Vector3d(1.0, 0.0, 0.0)
        
        nullNXOpen_Point = NXOpen.Point.Null
        
        direction_x = workPart.Directions.CreateDirection(origin_pt, vector_x, NXOpen.SmartObject.UpdateOption.WithinModeling)
        axis1 = workPart.Axes.CreateAxis(nullNXOpen_Point, direction_x, NXOpen.SmartObject.UpdateOption.WithinModeling)
        revolveBuilder1.Axis = axis1
        
        log("Step 3: Commiting Revolve Feature...")
        revolve_feature = revolveBuilder1.CommitFeature()
        revolveBuilder1.Destroy()
        
        log("Step 3: Revolve (Solid Body) Created.")

        # ---- 4. 抽壳/加厚给顶成实体 (ShellBuilder) ----
        log("Step 4: Starting ShellBuilder...")
        shellBuilder1 = workPart.Features.CreateShellBuilder(nullNXOpen_Features_Feature)
        
        # 放宽公差以满足存在鼻锥顶点尖端时的偏置容差
        shellBuilder1.Tolerance = 0.05
        shellBuilder1.UseSurfaceApproximation = True
        shellBuilder1.SetDefaultThickness(str(thickness))
        
        body_obj = revolve_feature.GetBodies()[0]
        shellBuilder1.Body = body_obj
        
        # --- 寻找底面自动开口 ---
        log("Identifying base face for shelling...")
        faces_to_remove = []
        for idx, f in enumerate(body_obj.GetFaces()):
            try:
                ftype = f.SolidFaceType
                log(f"Face {idx}: type={ftype}")
                # 在 NXOpen 中, FaceType 的 Integer 值含义: 1为Planar(平面), 5为B-Surface(样条曲面)
                # 所以我们只提取 Type == 1 的平面作为去除面(开口面)
                if str(ftype) == "1" or ftype == getattr(NXOpen.Face.FaceType, 'Planar', -1):
                    faces_to_remove.append(f)
            except Exception as face_err:
                log(f"Face check error: {face_err}")
                
        if len(faces_to_remove) > 0:
            log(f"Found {len(faces_to_remove)} planar faces to pierce. Applying to Shell Builder.")
            scCollector1 = workPart.ScCollectors.CreateCollector()
            rules_array2 = []
            for face in faces_to_remove:
                # 使用简单的 Dumb 规则提取特定面，不产生相切蔓延
                faceDumbRule = workPart.ScRuleFactory.CreateRuleFaceDumb([face])
                rules_array2.append(faceDumbRule)
                
            scCollector1.ReplaceRules(rules_array2, False)
            shellBuilder1.RemovedFacesCollector = scCollector1
        else:
            log("No planar faces found, skipping piercing.")
        # ------------------------
        
        shellBuilder1.Commit()
        shellBuilder1.Destroy()
        
        log(f"Step 4: Shelling Applied with thickness {thickness} mm.")
        
        # 保存文件
        log("Step 5: Saving part...")
        workPart.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)
        log("All steps completed successfully.")
        
    except Exception as e:
        import traceback
        log("ERROR THROWN:")
        log(str(e))
        log(traceback.format_exc())
    finally:
        debug_log.close()

if __name__ == '__main__':
    import sys
    diameter = 110.0
    length = 300.0
    thickness = 2.0
    
    # Parse arguments provided via run_journal.exe -args
    for arg in sys.argv:
        if arg.startswith("Diameter="):
            diameter = float(arg.split("=")[1])
        elif arg.startswith("Length="):
            length = float(arg.split("=")[1])
        elif arg.startswith("Thickness="):
            thickness = float(arg.split("=")[1])
            
    create_fairing(diameter, length, thickness)
