                                                                                                                
                                                                                                                 
const ARC = 'arc-public-hex-v1';
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const fail = message => { throw new Error('Public observation codec: ' + message); };
const copy = value => structuredClone(value);

export const ARC_PUBLIC_DECODING_INSTRUCTIONS = 'Lossless public ARC frame encoding. Every layer is {width,height,rows}; rows[y][x] is the exact cell at coordinate (x,y), origin top-left. Palette digits 0-9,A-F mean integers 0-15. Decode each fixed-width row character as one hexadecimal integer; preserve layer order. All remaining data fields are original public metadata, including available_actions and transport feedback. This is structured grid input.';

export function encodeArcPublicFrame(data) {
  if (!object(data) || !Array.isArray(data.frame) || !data.frame.length) fail('ARC frame layers missing');
  const frame = data.frame.map(layer => {
    if (!Array.isArray(layer) || !layer.length || !Array.isArray(layer[0]) || !layer[0].length) fail('ARC layer shape');
    const width = layer[0].length, height = layer.length;
    if (width > 64 || height > 64) fail('ARC layer dimensions exceed official limit');
    const rows = layer.map(row => {
      if (!Array.isArray(row) || row.length !== width || row.some(value => !Number.isInteger(value) || value < 0 || value > 15)) fail('ARC palette or rectangular shape');
      return row.map(value => value.toString(16).toUpperCase()).join('');
    });
    return { width, height, rows };
  });
  return { codec: ARC, data: { ...copy(data), frame } };
}

                                                                                                                 
export function encodeArcObservation(observation) {
  if (!object(observation) || typeof observation.publicText !== 'string') fail('observation publicText missing');
  const rawText = observation.publicText;
  const original = JSON.parse(rawText);
  const encoded = encodeArcPublicFrame(original);
  const compact = packLayers(encoded.data.frame);
  const text = 'Lossless ARC row-delta encoding v2. Palette 0-9,A-F; origin top-left (x,y). rowTable stores exact grid rows. Each frame entry updates the preceding rowIds using [y,rowTableIndex] pairs (the first entry supplies all rows); expand repeat to recover identical consecutive layers. Preserve frame order. The final layer is the latest visible state. Native metadata is unchanged.\n'
    + JSON.stringify({codec:'arc-public-row-delta-v2',data:{...encoded.data,frame:compact.frames,rowTable:compact.rowTable}});
  if (text.length >= rawText.length) return observation;
  return { ...observation, publicText: text };
}

export function packLayers(layers) {
  const rowTable=[], index=new Map(), frames=[];
  let previous=[];
  for(const layer of layers){
    const ids=layer.rows.map(row=>{if(!index.has(row)){index.set(row,rowTable.length);rowTable.push(row);}return index.get(row);});
    const last=frames.at(-1);
    const sameShape=last&&last.width===layer.width&&last.height===layer.height;
    const updates=ids.flatMap((id,y)=>sameShape&&previous[y]===id?[]:[[y,id]]);
    if(sameShape&&updates.length===0)last.repeat++;
    else frames.push({width:layer.width,height:layer.height,updates,repeat:1});
    previous=ids;
  }
  return {rowTable,frames};
}

export function unpackLayers({rowTable,frames}) {
  let rows=[]; const result=[];
  for(const frame of frames){
    if(rows.length!==frame.height||rows[0]?.length!==frame.width)rows=Array(frame.height);
    for(const [y,id] of frame.updates)rows[y]=rowTable[id];
    if(rows.some(row=>typeof row!=='string'||row.length!==frame.width))fail('Incomplete delta frame');
    for(let i=0;i<frame.repeat;i++)result.push({width:frame.width,height:frame.height,rows:[...rows]});
  }
  return result;
}
