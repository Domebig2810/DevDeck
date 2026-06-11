// Globale Typen: Spiegel der Python-Dataclasses (models/configuration.py)
// und der pywebview-JS-Bridge (api.py).

interface ButtonConfig {
  label: string;
  command: string;
  image: string;
  display_mode: "label" | "image";
  /** Base64-Data-URL, wird vom Backend bei load_all/convert_image mitgeliefert */
  image_preview?: string;
}

interface EncoderConfig {
  label: string;
  step: number;
  clockwise_command: string;
  counter_command: string;
  click_command: string;
}

interface Config {
  name: string;
  buttons: ButtonConfig[];
  encoders: EncoderConfig[];
}

/** Alle Methoden aus api.py, via pywebview als Promise exponiert */
interface PyWebviewApi {
  [method: string]: (...args: any[]) => Promise<any>;
}

interface Window {
  pywebview?: { api: PyWebviewApi };
}
