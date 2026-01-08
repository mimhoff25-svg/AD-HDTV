#!/usr/bin/env python3
"""
Performance test for WebGridPlayer 8-video optimizations
"""
import sys
import time
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    import vlc
    print("✅ VLC Python bindings available")
    
    # Test VLC instance creation with optimized args
    print("🧪 Testing optimized VLC instance creation...")
    
    vlc_args = [
        '--quiet',
        '--no-video-title-show', 
        '--network-caching=500',
        '--live-caching=300',
        '--http-reconnect',
        '--avcodec-hw=any',
        '--no-stats',
        '--no-osd',
        '--intf=dummy',
        '--verbose=0',
    ]
    
    start_time = time.time()
    instance = vlc.Instance(vlc_args)
    creation_time = time.time() - start_time
    
    if instance:
        print(f"✅ Optimized VLC instance created in {creation_time:.3f}s")
        
        # Test media player creation
        player = instance.media_player_new()
        if player:
            print("✅ Media player created successfully")
            
            # Test hardware acceleration detection
            print("🔍 Checking hardware acceleration capabilities...")
            print(f"   VLC Version: {vlc.libvlc_get_version().decode() if vlc.libvlc_get_version else 'Unknown'}")
            
            player.release()
        else:
            print("❌ Failed to create media player")
            
        instance.release()
    else:
        print("❌ Failed to create VLC instance")
        
except ImportError as e:
    print(f"❌ VLC not available: {e}")
    sys.exit(1)

# Test threading capability
try:
    from concurrent.futures import ThreadPoolExecutor
    print("✅ ThreadPoolExecutor available")
    
    # Test 8-thread pool creation
    with ThreadPoolExecutor(max_workers=8, thread_name_prefix='webgrid-test') as executor:
        print("✅ 8-worker thread pool created successfully")
        
        # Test concurrent task submission
        futures = []
        for i in range(8):
            future = executor.submit(time.sleep, 0.1)
            futures.append(future)
        
        # Wait for all tasks
        for future in futures:
            future.result()
        print("✅ 8 concurrent tasks completed")
        
except Exception as e:
    print(f"❌ Threading test failed: {e}")

# Test performance monitoring dependencies
try:
    import psutil
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    cpu_percent = process.cpu_percent()
    print(f"✅ Performance monitoring available")
    print(f"   Current RAM usage: {memory_mb:.1f}MB")
    print(f"   Current CPU usage: {cpu_percent:.1f}%")
except ImportError:
    print("⚠️  psutil not available - performance monitoring will be limited")
    print("   Install with: pip install psutil")

# Test PyQt availability
try:
    from PyQt6.QtWidgets import QApplication
    print("✅ PyQt6 available")
except ImportError:
    try:
        from PyQt5.QtWidgets import QApplication  
        print("✅ PyQt5 available")
    except ImportError:
        print("❌ Neither PyQt6 nor PyQt5 available")

print("\n🎬 WebGridPlayer 8-video optimization test completed!")
print("\nRecommendations for optimal 8-video performance:")
print("• Use hardware-accelerated video formats (H.264/H.265)")
print("• Ensure good network bandwidth (50-100Mbps recommended)")  
print("• Close other video applications")
print("• Monitor memory usage (aim for <3GB with 8 videos)")
print("• Consider 2x3 grid (6 videos) for better performance on older systems")