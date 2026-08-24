from build123d import *
import os

# --- Parameters ---
edf_od = 74.0  # Outer diameter of the EDF shroud
clearance = 0.2
wall_thickness = 3.0
servo_w = 12.5
servo_l = 23.5
servo_h = 27.0
mount_height = 25.0

# Derived
ring_id = edf_od + clearance
ring_od = ring_id + wall_thickness * 2
gimbal_gap = 1.5

def create_servo_cutout():
    """Creates a basic box for SG92R servo cutout"""
    with BuildPart() as servo:
        # Main body
        Box(servo_l, servo_w, servo_h)
        # Mounting ears (simplified)
        with BuildPart(mode=Mode.ADD) as ears:
            Box(32.5, servo_w, 2.5, align=(Align.CENTER, Align.CENTER, Align.MIN))
            # Offset ears to the top position (approx)
            ears.part.move(Location((0, 0, 5)))
    return servo.part

def generate_tvc():
    # 1. Base Mount (Attaches to EDF)
    with BuildPart() as base_mount:
        with BuildSketch() as s:
            Circle(ring_od / 2)
            Circle(ring_id / 2, mode=Mode.SUBTRACT)
        extrude(amount=mount_height)
        
        # Add pivot mounts for the first gimbal (Yaw)
        # Positioned at 0 and 180 degrees
        pivot_block_size = 8
        with BuildPart(mode=Mode.ADD):
            with Locations((0, ring_od/2 + pivot_block_size/2 - 1, mount_height/2), 
                           (0, -(ring_od/2 + pivot_block_size/2 - 1), mount_height/2)):
                Box(10, pivot_block_size, 10)
        
        # Pivot holes (M3)
        with BuildPart(mode=Mode.SUBTRACT):
            with Locations((0, ring_od/2 + 5, mount_height/2),
                           (0, -(ring_od/2 + 5), mount_height/2)):
                # Rotate hole to be along Y axis
                add(Rotation(90, 0, 0) * Cylinder(radius=1.6, height=30))

        # Servo mount for Yaw
        with Locations((ring_od/2 + 5, 0, mount_height/2)):
            Box(20, servo_w + 6, mount_height, align=(Align.MIN, Align.CENTER, Align.CENTER))
            with BuildPart(mode=Mode.SUBTRACT):
                # Cutout for servo
                add(Location((10, 0, 0)) * create_servo_cutout())

    # 2. Outer Gimbal (Yaw Ring)
    gimbal_yaw_id = ring_od + gimbal_gap
    gimbal_yaw_od = gimbal_yaw_id + wall_thickness * 2
    
    with BuildPart() as gimbal_yaw:
        with BuildSketch() as s2:
            Circle(gimbal_yaw_od / 2)
            Circle(gimbal_yaw_id / 2, mode=Mode.SUBTRACT)
        extrude(amount=10)
        
        # Pivot pins/holes for connection to Base (at 0 and 180)
        # These match the base_mount holes
        with BuildPart(mode=Mode.ADD):
            with Locations((0, gimbal_yaw_id/2 - 2, 5), (0, -(gimbal_yaw_id/2 - 2), 5)):
                add(Rotation(90, 0, 0) * Cylinder(radius=1.5, height=6))
                
        # Pivot holes for inner nozzle (at 90 and 270)
        with BuildPart(mode=Mode.SUBTRACT):
            with Locations((gimbal_yaw_od/2 + 2, 0, 5), (-(gimbal_yaw_od/2 + 2), 0, 5)):
                add(Rotation(0, 90, 0) * Cylinder(radius=1.6, height=20))
                
        # Servo mount for Pitch (rides on the Yaw ring)
        with Locations((0, gimbal_yaw_od/2 + 5, 5)):
             Box(servo_w + 6, 20, 25, align=(Align.CENTER, Align.MIN, Align.CENTER))
             with BuildPart(mode=Mode.SUBTRACT):
                 # Cutout for servo
                 add(Location((0, 10, 0)) * Rotation(0,0,90) * create_servo_cutout())

    # 3. Inner Nozzle (Pitch)
    nozzle_id = ring_id - 2
    nozzle_od = nozzle_id + wall_thickness
    
    with BuildPart() as nozzle:
        with BuildSketch() as s3:
            Circle(nozzle_od / 2)
            Circle(nozzle_id / 2, mode=Mode.SUBTRACT)
        extrude(amount=30) # Longer for flow guidance
        
        # Pivot pins for Pitch (at 90 and 270)
        with BuildPart(mode=Mode.ADD):
            with Locations((nozzle_od/2 - 1, 0, 15), (-(nozzle_od/2 - 1), 0, 15)):
                add(Rotation(0, 90, 0) * Cylinder(radius=1.5, height=10))


    # Export
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
        
    export_step(base_mount.part, "outputs/base_mount.step")
    export_stl(base_mount.part, "outputs/base_mount.stl")
    
    export_step(gimbal_yaw.part, "outputs/gimbal_yaw.step")
    export_stl(gimbal_yaw.part, "outputs/gimbal_yaw.stl")
    
    export_step(nozzle.part, "outputs/nozzle.step")
    export_stl(nozzle.part, "outputs/nozzle.stl")
    
    # Combined for preview/assembly reference
    assembly = Compound(children=[base_mount.part, gimbal_yaw.part.move(Location((0,0, mount_height + 5))), nozzle.part.move(Location((0,0, mount_height + 25)))])
    export_step(assembly, "outputs/full_assembly.step")

    print("Generation complete. Files saved in 'outputs/' directory.")

if __name__ == "__main__":
    generate_tvc()
