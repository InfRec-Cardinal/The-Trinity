                                                                       
import { deflateSync } from 'node:zlib';

const crcTable = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
function crc(bytes) { let c = 0xffffffff; for (const b of bytes) c = crcTable[(c ^ b) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; }
function chunk(type, data) { const name = Buffer.from(type), length = Buffer.alloc(4), checksum = Buffer.alloc(4); length.writeUInt32BE(data.length); checksum.writeUInt32BE(crc(Buffer.concat([name, data]))); return Buffer.concat([length, name, data, checksum]); }
const GLYPHS = {
  '0':['111','101','101','101','111'],'1':['010','110','010','010','111'],'2':['111','001','111','100','111'],'3':['111','001','111','001','111'],
  '4':['101','101','111','001','001'],'5':['111','100','111','001','111'],'6':['111','100','111','101','111'],'7':['111','001','010','010','010'],
  '8':['111','101','111','101','111'],'9':['111','101','111','001','111'],'A':['010','101','111','101','101'],'B':['110','101','110','101','110'],
  'C':['111','100','100','100','111'],'D':['110','101','101','101','110'],'E':['111','100','110','100','111'],'F':['111','100','110','100','100'],
  'G':['111','100','101','101','111'],'H':['101','101','111','101','101'],'I':['111','010','010','010','111'],'J':['001','001','001','101','111'],
  'K':['101','101','110','101','101'],'L':['100','100','100','100','111'],'M':['101','111','111','101','101'],'N':['101','111','111','111','101'],
  'O':['111','101','101','101','111'],'P':['111','101','111','100','100'],'Q':['111','101','101','111','001'],'R':['110','101','110','101','101'],
  'S':['111','100','111','001','111'],'T':['111','010','010','010','010'],'U':['101','101','101','101','111'],'V':['101','101','101','101','010'],
  'W':['101','101','111','111','101'],'X':['101','101','010','101','101'],'Y':['101','101','010','010','010'],'Z':['111','001','010','100','111'],
  '-':['000','000','111','000','000'],'?':['111','001','010','000','010'],'*':['010','111','010','101','000'],'.':['000','000','000','000','010'],
  ':':['000','010','000','010','000'],'/':['001','001','010','100','100'],'+':['000','010','111','010','000'],' ':['000','000','000','000','000'],
};
export class Raster {
  constructor(width = 640, height = 420, background = [245,248,251]) { this.width = width; this.height = height; this.pixels = Buffer.alloc(width * height * 3); this.rect(0, 0, width, height, background); }
  pixel(x, y, color) { x = Math.round(x); y = Math.round(y); if (x < 0 || y < 0 || x >= this.width || y >= this.height) return; const p = (y * this.width + x) * 3; for (let c = 0; c < 3; c++) this.pixels[p+c] = color[c]; }
  rect(x, y, w, h, color) { for (let j = Math.max(0, Math.floor(y)); j < Math.min(this.height, Math.ceil(y+h)); j++) for (let i = Math.max(0, Math.floor(x)); i < Math.min(this.width, Math.ceil(x+w)); i++) this.pixel(i,j,color); }
  circle(x, y, r, color) { for (let j = Math.floor(y-r); j <= y+r; j++) for (let i = Math.floor(x-r); i <= x+r; i++) if ((i-x)**2+(j-y)**2 <= r*r) this.pixel(i,j,color); }
  line(x1, y1, x2, y2, color, thickness = 2) { const n = Math.max(1, Math.ceil(Math.hypot(x2-x1,y2-y1))); for (let i=0;i<=n;i++) this.circle(x1+(x2-x1)*i/n,y1+(y2-y1)*i/n,thickness/2,color); }
  text(value, x, y, color = [38,54,72], scale = 3) { for (const char of String(value).toUpperCase()) { const g=GLYPHS[char]??GLYPHS['?']; for (let r=0;r<5;r++) for(let c=0;c<3;c++) if(g[r][c]==='1') this.rect(x+c*scale,y+r*scale,scale,scale,color); x+=4*scale; } }
  png() { const header=Buffer.alloc(13);header.writeUInt32BE(this.width,0);header.writeUInt32BE(this.height,4);header[8]=8;header[9]=2;const rows=Buffer.alloc((this.width*3+1)*this.height);for(let y=0;y<this.height;y++)this.pixels.copy(rows,y*(this.width*3+1)+1,y*this.width*3,(y+1)*this.width*3);return Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]),chunk('IHDR',header),chunk('IDAT',deflateSync(rows)),chunk('IEND',Buffer.alloc(0))]); }
}
export const palette = [[58,132,198],[248,179,61],[153,100,199],[43,163,127],[219,90,112],[112,137,160],[139,173,80],[202,130,65]];
export function gridCanvas(width,height,tile=32){return new Raster(width*tile+32,height*tile+64);}
export function drawGrid(r,grid,colors,tile=32){for(let y=0;y<grid.length;y++)for(let x=0;x<grid[y].length;x++){r.rect(16+x*tile,48+y*tile,tile-2,tile-2,colors[grid[y][x]]??[220,227,233]);}}
