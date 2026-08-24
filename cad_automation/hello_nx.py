import math
import NXOpen
import NXOpen.Features

def main():
    theSession  = NXOpen.Session.GetSession()
    workPart = theSession.Parts.Work

    # 如果当前没有打开的模型文件，自动创建一个新的空白文档
    if workPart is None:
        newFile = theSession.Parts.FileNew()
        newFile.NewFileName = "ad_astra_test.prt"
        newFile.Units = NXOpen.Part.Units.Millimeters
        newFile.UseBlankTemplate = True
        newFile.MakeDisplayedPart = True
        newFile.Commit()
        workPart = theSession.Parts.Work
        newFile.Destroy()

    theSession.ListingWindow.Open()
    theSession.ListingWindow.WriteLine("-------------------------------------")
    theSession.ListingWindow.WriteLine("Project Ad Astra: Cad Automation Node")
    theSession.ListingWindow.WriteLine("System Status: Online")
    theSession.ListingWindow.WriteLine("-------------------------------------")

    # 创建一个测试用的长方体 block (验证 API 参数化驱动能力)
    try:
        blockBuilder = workPart.Features.CreateBlockFeatureBuilder(NXOpen.Features.Feature.Null)
        blockBuilder.Type = NXOpen.Features.BlockFeatureBuilder.Types.OriginAndEdgeLengths
        
        # 尺寸参数：X=100, Y=50, Z=200
        blockBuilder.SetOriginAndLengths(
            NXOpen.Point3d(0.0, 0.0, 0.0), "100", "50", "200"
        )
        blockBuilder.CommitFeature()
        blockBuilder.Destroy()
        
        theSession.ListingWindow.WriteLine("Operation Success: Block parameterization implemented.")
        
        # 自动保存在当前工作目录
        partSaveStatus = workPart.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)
        partSaveStatus.Dispose()
        theSession.ListingWindow.WriteLine("Model Saved successfully.")
        
    except Exception as e:
        theSession.ListingWindow.WriteLine("ERROR: " + str(e))

if __name__ == '__main__':
    main()
