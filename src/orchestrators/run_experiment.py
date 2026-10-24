import subprocess
import os
import sys

def run_cpp_engine(topology_json, output_dir):
    # 1. Determine absolute root path of the toolkit
    current_dir = os.path.dirname(os.path.abspath(__file__))
    toolkit_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    
    # 2. Path to the compiled C++ binary in lib/
    cpp_binary = os.path.join(toolkit_root, "lib", "scmbn-core", "build", "scientific_benchmarking")
    
    if not os.path.exists(cpp_binary):
        print(f"❌ Error: Binary not found at {cpp_binary}")
        print("Please make sure scmbn-core is compiled inside the lib/ folder.")
        sys.exit(1)
        
    print(f"🚀 Launching C++ Engine: {cpp_binary}")
    print(f"📂 Analyzing Network: {topology_json}")
    
    # 3. Execute the C++ engine with debug dump enabled
    result = subprocess.run([
        cpp_binary, 
        "--input", topology_json, 
        "--dir", output_dir,
        "--debug-dump"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ Experiment completed successfully.")
        print(f"📊 Results securely saved in: {output_dir}")
        if result.stdout:
            print("\n--- C++ Engine Log ---")
            print(result.stdout)
    else:
        print(f"❌ C++ Execution Error: {result.stderr}")
        sys.exit(1)

if __name__ == "__main__":
    # Dynamic path configuration
    current_dir = os.path.dirname(os.path.abspath(__file__))
    toolkit_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    
    # Strictly point to the updated model
    test_json = os.path.join(toolkit_root, "data", "drosophila_update.json") 
    out_dir = os.path.join(toolkit_root, "data", "results")
    
    # Ensure output directory exists
    os.makedirs(out_dir, exist_ok=True)
    
    if os.path.exists(test_json):
        run_cpp_engine(test_json, out_dir)
    else:
        print(f"❌ Error: Target file not found: {test_json}")
        print("💡 Run the generator first: python3 src/generators/generate_drosophila_update.py")