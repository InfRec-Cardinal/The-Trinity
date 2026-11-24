                                               

from pathlib import Path

                         
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "ale-bench"

                       
DOCKER_HUB_REPO = "ale-bench"

                         
HUGGING_FACE_REPO = "SakanaAI/ALE-Bench"

                                          
RUST_TOOL_DOCKER_IMAGE = "rust:1.79.0-buster"

                                                   
VIS_SERVER_DOCKER_IMAGE = "httpd:2.4.63-bookworm"

                                                          
ALLOW_SCORE_NON_AC_PUBLIC = {
    "ahc016",
    "ahc017",
    "ahc018",
    "ahc019",
    "ahc022",
    "ahc025",
    "ahc027",
    "ahc029",
    "ahc030",
    "ahc031",
    "ahc033",
    "ahc036",
    "ahc038",
    "ahc040",
    "ahc043",
    "ahc045",
}                         
ALLOW_SCORE_NON_AC_PRIVATE = {
    "ahc001",
    "ahc003",
    "ahc008",
    "ahc011",
    "ahc013",
    "ahc014",
    "ahc016",
    "ahc017",
    "ahc018",
    "ahc019",
    "ahc022",
    "ahc023",
    "ahc025",
    "ahc027",
    "ahc029",
    "ahc030",
    "ahc031",
    "ahc033",
    "ahc036",
    "ahc038",
    "ahc040",
    "ahc043",
    "ahc045",
    "ahc048",
    "ahc051",
    "awtf2025heuristic",
    "future-contest-2022-qual",
}                       
NO_LOCAL_VIS = {"ahc016"}
VIS_SVG_GENERATION = {"ahc002", "ahc003", "ahc004", "ahc005", "future-contest-2022-qual", "ahc006", "ahc007", "ahc009"}
NO_EXAMPLE_INOUT = {"ahc003", "future-contest-2022-qual"}

                                    
WORK_DIR = "/workdir"
JUDGE_DIR = "/judge"
TMP_DIR = str(Path("/", "tmp"))

GEN_BIN = f"{JUDGE_DIR}/target/release/gen"
TESTER_BIN = f"{JUDGE_DIR}/target/release/tester"
VIS_BIN = f"{JUDGE_DIR}/target/release/vis"
VIS_SERVER_DIR = "/usr/local/apache2/htdocs"

SEEDS_FILE = f"{TMP_DIR}/seeds.txt"
IN_DIR = f"{WORK_DIR}/in"

INPUT_FILE = f"{TMP_DIR}/input.txt"
OUTPUT_FILE = f"{TMP_DIR}/output.txt"
PROFILES_FILE = f"{TMP_DIR}/profiles.json"
LOCAL_VIS_SVG = f"{WORK_DIR}/out.svg"
LOCAL_VIS_HTML = f"{WORK_DIR}/vis.html"

             
ERROR_CODE_137 = 137                                                          

       
REJECTED_ABSOLUTE_SCORE = 0

         
GENERATION_TIMEOUT = 300               
COMPILE_TIMEOUT = 60              
VISUALIZE_TIMEOUT = 10              

                                              
MAX_MEMORY_LIMIT = 2 * 1024 * 1024 * 1024         

                                               
TIME_OUTPUT_FORMAT = (
    "{"
    '\\"command\\": \\"%C\\", '
    '\\"exit_status\\": \\"%x\\", '
    '\\"elapsed_time\\": \\"%E\\", '
    '\\"elapsed_time_seconds\\": \\"%e\\", '
    '\\"system_cpu_seconds\\": \\"%S\\", '
    '\\"user_cpu_seconds\\": \\"%U\\", '
    '\\"cpu_percent\\": \\"%P\\", '
    '\\"average_resident_set_size_kbytes\\": \\"%t\\", '
    '\\"max_resident_set_size_kbytes\\": \\"%M\\", '
    '\\"average_total_memory_kbytes\\": \\"%K\\", '
    '\\"signals_delivered\\": \\"%k\\", '
    '\\"page_size_bytes\\": \\"%Z\\", '
    '\\"minor_page_faults\\": \\"%R\\", '
    '\\"major_page_faults\\": \\"%F\\", '
    '\\"swaps\\": \\"%W\\", '
    '\\"file_system_inputs\\": \\"%I\\", '
    '\\"file_system_outputs\\": \\"%O\\", '
    '\\"average_shared_text_kbytes\\": \\"%X\\", '
    '\\"average_unshared_data_kbytes\\": \\"%D\\", '
    '\\"average_unshared_stack_kbytes\\": \\"%p\\", '
    '\\"voluntary_context_switches\\": \\"%w\\", '
    '\\"involuntary_context_switches\\": \\"%c\\", '
    '\\"socket_messages_sent\\": \\"%s\\", '
    '\\"socket_messages_received\\": \\"%r\\"'
    "}"
)
