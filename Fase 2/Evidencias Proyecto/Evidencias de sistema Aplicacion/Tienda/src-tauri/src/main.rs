use std::{fs, sync::Mutex};
use tauri::{Manager, RunEvent};
use tauri_plugin_shell::{
    process::{CommandChild, CommandEvent},
    ShellExt,
};

struct SidecarState(Mutex<Option<CommandChild>>);

fn main() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(SidecarState(Mutex::new(None)))
        .setup(|app| {
            // La base incluida es una semilla de solo lectura. En el primer arranque
            // se copia al directorio escribible y persistente de la aplicación.
            let data_dir = app.path().app_data_dir()?;
            fs::create_dir_all(&data_dir)?;
            let database = data_dir.join("girasol.db");
            if !database.exists() {
                let bundled_database = app.path().resource_dir()?.join("data/girasol.db");
                fs::copy(&bundled_database, &database).map_err(|error| {
                    format!(
                        "No se pudo preparar la base de datos desde {}: {error}",
                        bundled_database.display()
                    )
                })?;
            }

            let invoice_dir = data_dir.join("facturas");
            let database_env = data_dir.join("database.env");
            let sidecar = app
                .shell()
                .sidecar("tienda-api")?
                .env("GIRASOL_DB_PATH", &database)
                .env("FACTURAS_UPLOAD_DIR", &invoice_dir)
                .env("DB_ENV_FILE", &database_env);
            let (mut events, child) = sidecar.spawn()?;
            *app.state::<SidecarState>().0.lock().unwrap() = Some(child);

            tauri::async_runtime::spawn(async move {
                while let Some(event) = events.recv().await {
                    match event {
                        CommandEvent::Stdout(line) => {
                            println!("[tienda-api] {}", String::from_utf8_lossy(&line));
                        }
                        CommandEvent::Stderr(line) => {
                            eprintln!("[tienda-api] {}", String::from_utf8_lossy(&line));
                        }
                        CommandEvent::Error(error) => eprintln!("[tienda-api] {error}"),
                        CommandEvent::Terminated(status) => {
                            eprintln!("[tienda-api] proceso terminado: {status:?}");
                        }
                        _ => {}
                    }
                }
            });
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Tauri app");

    app.run(|handle, event| {
        if let RunEvent::Exit = event {
            if let Some(child) = handle.state::<SidecarState>().0.lock().unwrap().take() {
                let _ = child.kill();
            }
        }
    });
}
