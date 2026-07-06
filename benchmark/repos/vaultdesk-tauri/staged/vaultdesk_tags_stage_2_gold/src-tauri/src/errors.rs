use serde::{Deserialize, Serialize};
use std::fmt;

/// Normalized error shape shared across the command surface and read by the
/// frontend. Every failing command returns one of these.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct AppError {
    pub code: String,
    pub message: String,
}

impl AppError {
    pub fn new(code: &str, message: &str) -> Self {
        AppError {
            code: code.to_string(),
            message: message.to_string(),
        }
    }

    /// A requested path resolved outside the permitted vault boundary.
    pub fn path_escape(detail: &str) -> Self {
        AppError::new("PATH_ESCAPE", detail)
    }

    /// The supplied input could not be parsed into the expected shape.
    pub fn invalid_input(detail: &str) -> Self {
        AppError::new("INVALID_INPUT", detail)
    }

    /// A requested resource was not present.
    pub fn not_found(detail: &str) -> Self {
        AppError::new("NOT_FOUND", detail)
    }
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}: {}", self.code, self.message)
    }
}

impl std::error::Error for AppError {}
