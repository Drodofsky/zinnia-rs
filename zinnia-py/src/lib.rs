use std::path::Path;

use pyo3::exceptions::PyRuntimeError;
use pyo3::prelude::*;
use zinnia::{Character as RustCharacter, Error, Recognizer as RustRecognizer};

#[pyclass]
pub struct Recognizer {
    inner: RustRecognizer,
}
#[pyclass]
pub struct Character {
    inner: RustCharacter,
}

#[pymethods]
impl Recognizer {
    #[new]
    fn new() -> Self {
        Self {
            inner: RustRecognizer::new(),
        }
    }

    fn open(&mut self, path: &str) -> PyResult<()> {
        self.inner.open(Path::new(path)).map_err(to_py_err)
    }

    fn classify(&self, character: &Character, nbest: usize) -> PyResult<Vec<(String, f32)>> {
        self.inner
            .classify(&character.inner, nbest)
            .map_err(to_py_err)
            .map(|v| v.into_iter().map(|c| (c.value, c.score)).collect())
    }
}

#[pymethods]
impl Character {
    #[new]
    pub fn new() -> Self {
        Self {
            inner: RustCharacter::new(),
        }
    }

    pub fn set_width(&mut self, width: usize) -> PyResult<()> {
        self.inner.set_width(width).map_err(to_py_err)
    }

    pub fn set_height(&mut self, height: usize) -> PyResult<()> {
        self.inner.set_height(height).map_err(to_py_err)
    }

    pub fn add(&mut self, stroke_id: usize, x: i32, y: i32) -> PyResult<()> {
        self.inner.add(stroke_id, x, y).map_err(to_py_err)
    }

    pub fn clear(&mut self) -> PyResult<()> {
        self.inner.clear().map_err(to_py_err)
    }
}
#[pymodule]
fn zinnia_py(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Recognizer>()?;
    m.add_class::<Character>()?;
    Ok(())
}

fn to_py_err(e: Error) -> PyErr {
    PyRuntimeError::new_err(format!("{e:?}"))
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;
    use std::process::Command;
    fn python_bin() -> &'static str {
        if cfg!(target_os = "windows") {
            "python"
        } else {
            "python3"
        }
    }
    fn venv_bin(venv: &PathBuf, bin: &str) -> PathBuf {
        if cfg!(target_os = "windows") {
            venv.join("Scripts").join(format!("{bin}.exe"))
        } else {
            venv.join("bin").join(bin)
        }
    }

    #[test]
    fn pytest() {
        let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let venv = manifest_dir.join(".venv-test");

        // create venv if it doesn't exist
        if !venv.exists() {
            let status = Command::new(python_bin())
                .args(["-m", "venv", venv.to_str().unwrap()])
                .status()
                .expect("python3 not found");
            assert!(status.success(), "venv creation failed");
        }

        // install pytest into the venv
        let status = Command::new(venv_bin(&venv, "pip"))
            .args(["install", "pytest", "--quiet"])
            .status()
            .expect("pip not found");
        assert!(status.success(), "pip install failed");

        // maturin develop into the venv
        let status = Command::new("maturin")
            .args(["develop"])
            .env("VIRTUAL_ENV", venv.to_str().unwrap())
            .current_dir(&manifest_dir)
            .status()
            .expect("maturin not found");
        assert!(status.success(), "maturin develop failed");

        // run pytest
        let status = Command::new(venv_bin(&venv, "pytest"))
            .args(["python_tests/", "-v"])
            .current_dir(&manifest_dir)
            .status()
            .expect("pytest not found");
        assert!(status.success(), "pytest failed");
    }
}
