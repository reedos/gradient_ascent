import { zipFiles } from './learning-labs';
export function downloadFiles(name: string, files: Record<string, string>) {
  const bytes = zipFiles(files);
  const link = document.createElement('a');
  const objectUrl = URL.createObjectURL(new Blob([bytes.buffer as ArrayBuffer], { type: 'application/zip' }));
  link.href = objectUrl; link.download = name; document.body.append(link); link.click(); link.remove();
  setTimeout(() => URL.revokeObjectURL(objectUrl), 1000);
}
