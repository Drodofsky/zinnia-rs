fn main() {
    let files = [
        "vendor/zinnia/param.cpp",
        "vendor/zinnia/recognizer.cpp",
        "vendor/zinnia/svm.cpp",
        "vendor/zinnia/sexp.cpp",
        "vendor/zinnia/feature.cpp",
        "vendor/zinnia/libzinnia.cpp",
        "vendor/zinnia/character.cpp",
    ];

    let mut build = cc::Build::new();
    build
        .cpp(true)
        .include("vendor/zinnia")
        .define("HAVE_CONFIG_H", "1")
        .flag_if_supported("-std=c++11")
        .flag_if_supported("-fPIC")
        .flag_if_supported("-w");

    for file in files {
        build.file(file);
        println!("cargo:rerun-if-changed={file}");
    }

    println!("cargo:rerun-if-changed=vendor/zinnia/config.h");
    println!("cargo:rerun-if-changed=build.rs");

    build.compile("zinnia");
}
