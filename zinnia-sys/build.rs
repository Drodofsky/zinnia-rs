use std::fs;
fn main() {
    // FIX
    let trainer_path = "vendor/zinnia/trainer.cpp";

    let content = fs::read_to_string(trainer_path).unwrap();

    let fixed = content.replace(
        "std::make_pair<std::string, FeatureNode *>(y, fn)",
        "std::make_pair(y, fn)",
    );

    fs::write(trainer_path, fixed).unwrap();

    let files = [
        "vendor/zinnia/param.cpp",
        "vendor/zinnia/recognizer.cpp",
        "vendor/zinnia/svm.cpp",
        "vendor/zinnia/sexp.cpp",
        "vendor/zinnia/feature.cpp",
        "vendor/zinnia/libzinnia.cpp",
        "vendor/zinnia/character.cpp",
        "vendor/zinnia/trainer.cpp",
    ];

    let mut build = cc::Build::new();

    build
        .cpp(true)
        .include("vendor/zinnia")
        .define("HAVE_CONFIG_H", "1")
        .define("DLL_EXPORT", "1")
        .flag_if_supported("-std=c++11")
        .flag_if_supported("-fPIC")
        .flag_if_supported("-w");

    if cfg!(target_os = "windows") {
        build
            .define("_CRT_SECURE_NO_WARNINGS", None)
            .define("HAVE_WINDOWS_H", None)
            .flag_if_supported("/EHsc")
            .flag_if_supported("/wd4996");
    }

    for file in files {
        build.file(file);
        println!("cargo:rerun-if-changed={file}");
    }

    println!("cargo:rerun-if-changed=vendor/zinnia/config.h");
    println!("cargo:rerun-if-changed=build.rs");

    build.compile("zinnia");
}
