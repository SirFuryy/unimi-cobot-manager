import pyzed.sl as sl
import numpy as np
import time
import os
from datetime import datetime

class Object3DReconstructor:
    def __init__(self, output_dir="3d_output"):
        """
        Inizializza il ricostruttore 3D per oggetti
        
        Args:
            output_dir: Directory per salvare mesh e point cloud
        """
        self.zed = sl.Camera()
        self.output_dir = output_dir
        
        # Crea directory di output
        os.makedirs(output_dir, exist_ok=True)
        
        # Parametri di inizializzazione ottimizzati per ricostruzione 3D
        init_params = sl.InitParameters()
        init_params.camera_resolution = sl.RESOLUTION.HD720  # Bilancio qualità/performance
        init_params.depth_mode = sl.DEPTH_MODE.ULTRA  # Massima qualità depth
        init_params.coordinate_units = sl.UNIT.METER
        init_params.depth_minimum_distance = 0.2  # 20cm minimo
        init_params.depth_maximum_distance = 2.0  # 2m massimo
        init_params.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
        
        # Apri la camera
        err = self.zed.open(init_params)
        if err != sl.ERROR_CODE.SUCCESS:
            print(f"❌ Errore apertura camera: {err}")
            exit(1)
        
        # Abilita tracking posizionale (necessario per spatial mapping)
        tracking_params = sl.PositionalTrackingParameters()
        tracking_params.enable_area_memory = True
        err = self.zed.enable_positional_tracking(tracking_params)
        if err != sl.ERROR_CODE.SUCCESS:
            print(f"❌ Errore abilitazione tracking: {err}")
            self.zed.close()
            exit(1)
        
        # Parametri runtime
        self.runtime_params = sl.RuntimeParameters()
        self.runtime_params.sensing_mode = sl.SENSING_MODE.FILL
        
        # Oggetti per dati 3D
        self.point_cloud = sl.Mat()
        self.mesh = sl.Mesh()
        
        print("✅ Camera ZED inizializzata per ricostruzione 3D")
        
    def setup_spatial_mapping(self, resolution_cm=2.0, max_range_m=1.5):
        """
        Configura lo spatial mapping
        
        Args:
            resolution_cm: Risoluzione della mesh in centimetri (più basso = più dettaglio)
            max_range_m: Distanza massima di mappatura in metri
        """
        mapping_params = sl.SpatialMappingParameters()
        
        # Imposta risoluzione (più basso = più dettaglio ma più lento)
        mapping_params.set_resolution(sl.MAPPING_RESOLUTION.MEDIUM)
        # In alternativa usa: LOW (5cm), MEDIUM (10cm), HIGH (2cm)
        
        # Imposta range massimo
        mapping_params.max_memory_usage = 2048  # MB
        mapping_params.save_texture = True  # Salva anche la texture
        mapping_params.use_chunk_only = True  # Usa chunks per oggetti
        mapping_params.reverse_vertex_order = False
        
        # Tipo di mappa
        mapping_params.map_type = sl.SPATIAL_MAP_TYPE.MESH
        
        # Abilita spatial mapping
        err = self.zed.enable_spatial_mapping(mapping_params)
        if err != sl.ERROR_CODE.SUCCESS:
            print(f"❌ Errore abilitazione spatial mapping: {err}")
            return False
        
        print(f"✅ Spatial mapping abilitato")
        print(f"   Risoluzione: MEDIUM (~10cm)")
        print(f"   Max memoria: 2048 MB")
        print(f"   Texture: Abilitata")
        
        return True
    
    def capture_for_reconstruction(self, duration_sec=30, min_frames=200):
        """
        Cattura dati per la ricostruzione 3D
        
        Args:
            duration_sec: Durata massima della cattura
            min_frames: Numero minimo di frame da catturare
        """
        print("\n" + "="*70)
        print("🎥 CATTURA DATI PER RICOSTRUZIONE 3D")
        print("="*70)
        print(f"\nDurata massima: {duration_sec}s")
        print(f"Frame minimi: {min_frames}")
        print("\nISTRUZIONI:")
        print("• Muovi LENTAMENTE la camera intorno all'oggetto")
        print("• Copri tutte le angolazioni (fronte, lati, alto, basso)")
        print("• Mantieni l'oggetto sempre inquadrato")
        print("• Evita movimenti bruschi")
        print("\nPremi INVIO per iniziare...")
        input()
        
        start_time = time.time()
        frame_count = 0
        mapping_state = sl.SPATIAL_MAPPING_STATE.NOT_ENABLED
        
        print("\n🔴 CATTURA IN CORSO...")
        print("Premi 'ESC' per terminare anticipatamente\n")
        
        while True:
            # Grab frame
            if self.zed.grab(self.runtime_params) == sl.ERROR_CODE.SUCCESS:
                frame_count += 1
                elapsed = time.time() - start_time
                
                # Ottieni stato del mapping
                mapping_state = self.zed.get_spatial_mapping_state()
                
                # Stampa progresso ogni 30 frame
                if frame_count % 30 == 0:
                    print(f"⏱️  {elapsed:.1f}s | Frame: {frame_count} | "
                          f"Mapping: {mapping_state}")
                
                # Condizioni di uscita
                if elapsed >= duration_sec:
                    print(f"\n⏱️  Tempo massimo raggiunto ({duration_sec}s)")
                    break
                
                if frame_count >= min_frames and elapsed >= 10:
                    # Permetti uscita anticipata dopo requisiti minimi
                    remaining = duration_sec - elapsed
                    if remaining <= 5 or frame_count % 60 == 0:
                        print(f"\n💡 Puoi premere ESC per terminare "
                              f"(frame: {frame_count}, tempo: {elapsed:.1f}s)")
                
                # Check ESC key (questo richiede OpenCV se vuoi usarlo)
                # Per semplicità usiamo solo il timeout
                time.sleep(0.001)
            
            else:
                print("⚠️  Errore nel grab frame")
                time.sleep(0.01)
        
        print(f"\n✅ Cattura completata!")
        print(f"   Frame catturati: {frame_count}")
        print(f"   Durata: {time.time() - start_time:.2f}s")
        
        return frame_count
    
    def extract_mesh(self, filter_params=None):
        """
        Estrae la mesh dalla spatial map
        
        Args:
            filter_params: Parametri di filtraggio (dict)
        """
        print("\n🔧 Estrazione mesh...")
        
        # Parametri di default per il filtraggio
        if filter_params is None:
            filter_params = {
                'filter_intensity': sl.MESH_FILTER.MEDIUM,
                'max_triangles': 500000
            }
        
        # Estrai mesh
        self.zed.extract_whole_spatial_map(self.mesh)
        
        nb_vertices = self.mesh.vertices.shape[0]
        nb_triangles = self.mesh.triangles.shape[0]
        
        print(f"✅ Mesh estratta!")
        print(f"   Vertici: {nb_vertices:,}")
        print(f"   Triangoli: {nb_triangles:,}")
        
        # Applica filtro
        print(f"\n🔧 Applicazione filtro: {filter_params['filter_intensity']}...")
        self.mesh.filter(filter_params['filter_intensity'], 
                        filter_params['max_triangles'])
        
        nb_vertices_filtered = self.mesh.vertices.shape[0]
        nb_triangles_filtered = self.mesh.triangles.shape[0]
        
        print(f"✅ Mesh filtrata!")
        print(f"   Vertici: {nb_vertices_filtered:,} "
              f"(-{nb_vertices - nb_vertices_filtered:,})")
        print(f"   Triangoli: {nb_triangles_filtered:,} "
              f"(-{nb_triangles - nb_triangles_filtered:,})")
        
        return self.mesh
    
    def crop_mesh_to_object(self, camera_distance_m=0.35, 
                           object_size_m=None,
                           crop_margin_m=0.10):
        """
        Ritaglia la mesh per isolare l'oggetto
        
        Args:
            camera_distance_m: Distanza della camera dall'oggetto (metri)
            object_size_m: Dimensioni stimate oggetto [larghezza, altezza, profondità] (metri)
                          Se None, usa dimensioni automatiche
            crop_margin_m: Margine extra attorno all'oggetto (metri)
        """
        print("\n✂️  Ritaglio mesh per isolare l'oggetto...")
        
        vertices = self.mesh.vertices
        if vertices.shape[0] == 0:
            print("❌ Nessun vertice nella mesh!")
            return
        
        # Calcola il centro della mesh (posizione media della camera)
        center = np.mean(vertices, axis=0)
        print(f"   Centro mesh: {center}")
        
        # Se non specificate, stima le dimensioni dell'oggetto
        if object_size_m is None:
            # Stima basata sulla distanza della camera
            # Assumendo FOV della ZED ~100° orizzontale
            fov_horizontal = np.radians(110)
            width_at_distance = 2 * camera_distance_m * np.tan(fov_horizontal / 2)
            
            # Stima dimensioni oggetto (80% della vista)
            estimated_width = width_at_distance * 0.6
            estimated_height = estimated_width * 0.8
            estimated_depth = estimated_width * 0.8
            
            object_size_m = [estimated_width, estimated_height, estimated_depth]
            print(f"   Dimensioni stimate oggetto: {object_size_m} m")
        
        # Calcola bounding box dell'oggetto
        half_width = (object_size_m[0] / 2) + crop_margin_m
        half_height = (object_size_m[1] / 2) + crop_margin_m
        half_depth = (object_size_m[2] / 2) + crop_margin_m
        
        # Definisci limiti del bounding box centrato
        bbox_min = center - np.array([half_width, half_height, half_depth])
        bbox_max = center + np.array([half_width, half_height, half_depth])
        
        print(f"   Bounding box:")
        print(f"     Min: {bbox_min}")
        print(f"     Max: {bbox_max}")
        
        # Filtra vertici dentro il bounding box
        mask = np.all((vertices >= bbox_min) & (vertices <= bbox_max), axis=1)
        
        num_vertices_before = vertices.shape[0]
        num_vertices_after = np.sum(mask)
        
        print(f"   Vertici prima: {num_vertices_before:,}")
        print(f"   Vertici dopo: {num_vertices_after:,}")
        print(f"   Rimossi: {num_vertices_before - num_vertices_after:,} "
              f"({(1 - num_vertices_after/num_vertices_before)*100:.1f}%)")
        
        if num_vertices_after == 0:
            print("⚠️  ATTENZIONE: Tutti i vertici sono stati rimossi!")
            print("    Prova ad aumentare object_size_m o crop_margin_m")
            return
        
        # Filtra anche i triangoli
        triangles = self.mesh.triangles
        if triangles.shape[0] > 0:
            # Mantieni solo triangoli i cui vertici sono tutti nel bbox
            valid_triangles_mask = np.all(mask[triangles], axis=1)
            
            # Crea nuovi indici per i vertici rimanenti
            vertex_mapping = np.cumsum(mask) - 1
            
            # Filtra e rimappa
            filtered_vertices = vertices[mask]
            filtered_triangles = vertex_mapping[triangles[valid_triangles_mask]]
            
            # Aggiorna la mesh
            self.mesh.vertices = filtered_vertices
            self.mesh.triangles = filtered_triangles
            
            # Filtra anche i colori se presenti
            if hasattr(self.mesh, 'colors') and self.mesh.colors.shape[0] > 0:
                self.mesh.colors = self.mesh.colors[mask]
            
            # Filtra le normali se presenti
            if hasattr(self.mesh, 'normals') and self.mesh.normals.shape[0] > 0:
                self.mesh.normals = self.mesh.normals[mask]
            
            print(f"   Triangoli dopo: {filtered_triangles.shape[0]:,}")
        
        print("✅ Mesh ritagliata con successo!")
    
    def extract_point_cloud(self):
        """Estrae la point cloud dall'ultimo frame"""
        print("\n☁️  Estrazione point cloud...")
        
        # Grab ultimo frame
        if self.zed.grab(self.runtime_params) == sl.ERROR_CODE.SUCCESS:
            self.zed.retrieve_measure(self.point_cloud, sl.MEASURE.XYZRGBA)
            
            # Converti in numpy
            pc_data = self.point_cloud.get_data()
            
            # Rimuovi punti invalidi (inf, nan)
            valid_mask = np.isfinite(pc_data).all(axis=2)
            
            num_points = np.sum(valid_mask)
            print(f"✅ Point cloud estratta: {num_points:,} punti validi")
            
            return pc_data, valid_mask
        else:
            print("❌ Errore nell'estrarre point cloud")
            return None, None
    
    def save_mesh(self, filename=None, file_format=sl.MESH_FILE_FORMAT.PLY):
        """
        Salva la mesh su file
        
        Args:
            filename: Nome file (None genera timestamp)
            file_format: Formato (PLY, OBJ, BIN)
        """
        if self.mesh.vertices.shape[0] == 0:
            print("❌ Nessuna mesh da salvare!")
            return None
        
        # Genera nome file
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = "ply" if file_format == sl.MESH_FILE_FORMAT.PLY else "obj"
            filename = f"object_mesh_{timestamp}.{ext}"
        
        filepath = os.path.join(self.output_dir, filename)
        
        # Salva
        print(f"\n💾 Salvataggio mesh...")
        print(f"   File: {filepath}")
        
        success = self.mesh.save(filepath, file_format)
        
        if success:
            file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB
            print(f"✅ Mesh salvata con successo! ({file_size:.2f} MB)")
            return filepath
        else:
            print("❌ Errore nel salvare la mesh")
            return None
    
    def save_point_cloud_ply(self, pc_data, valid_mask, filename=None):
        """
        Salva la point cloud in formato PLY
        
        Args:
            pc_data: Dati point cloud (numpy array)
            valid_mask: Maschera punti validi
            filename: Nome file
        """
        if pc_data is None:
            print("❌ Nessuna point cloud da salvare!")
            return None
        
        # Genera nome file
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"object_pointcloud_{timestamp}.ply"
        
        filepath = os.path.join(self.output_dir, filename)
        
        print(f"\n💾 Salvataggio point cloud...")
        print(f"   File: {filepath}")
        
        # Estrai punti validi
        points = pc_data[valid_mask]
        xyz = points[:, :3]
        rgb = points[:, 3].view(np.uint8).reshape(-1, 4)[:, :3]  # Estrai RGB
        
        # Scrivi file PLY
        with open(filepath, 'w') as f:
            # Header
            f.write("ply\n")
            f.write("format ascii 1.0\n")
            f.write(f"element vertex {len(xyz)}\n")
            f.write("property float x\n")
            f.write("property float y\n")
            f.write("property float z\n")
            f.write("property uchar red\n")
            f.write("property uchar green\n")
            f.write("property uchar blue\n")
            f.write("end_header\n")
            
            # Dati
            for i in range(len(xyz)):
                f.write(f"{xyz[i, 0]} {xyz[i, 1]} {xyz[i, 2]} "
                       f"{rgb[i, 0]} {rgb[i, 1]} {rgb[i, 2]}\n")
        
        file_size = os.path.getsize(filepath) / (1024 * 1024)  # MB
        print(f"✅ Point cloud salvata! ({file_size:.2f} MB)")
        
        return filepath
    
    def full_reconstruction(self, 
                          camera_distance_m=0.35,
                          object_size_m=None,
                          crop_margin_m=0.10,
                          capture_duration=30,
                          save_point_cloud=True):
        """
        Esegue una ricostruzione 3D completa
        
        Args:
            camera_distance_m: Distanza camera-oggetto in metri
            object_size_m: [larghezza, altezza, profondità] in metri
            crop_margin_m: Margine attorno all'oggetto
            capture_duration: Durata cattura in secondi
            save_point_cloud: Salva anche point cloud
        """
        print("\n" + "="*70)
        print("🎬 RICOSTRUZIONE 3D OGGETTO")
        print("="*70)
        print(f"\nPARAMETRI:")
        print(f"  Distanza camera: {camera_distance_m*100:.1f} cm")
        if object_size_m:
            print(f"  Dimensioni oggetto: {[f'{x*100:.1f}cm' for x in object_size_m]}")
        else:
            print(f"  Dimensioni oggetto: AUTO")
        print(f"  Margine crop: {crop_margin_m*100:.1f} cm")
        print(f"  Durata cattura: {capture_duration}s")
        print("="*70)
        
        # Setup spatial mapping
        if not self.setup_spatial_mapping():
            return
        
        # Cattura dati
        frame_count = self.capture_for_reconstruction(
            duration_sec=capture_duration,
            min_frames=200
        )
        
        if frame_count < 50:
            print("⚠️  ATTENZIONE: Pochi frame catturati, la qualità potrebbe essere bassa")
        
        # Estrai mesh
        self.extract_mesh()
        
        # Ritaglia per isolare l'oggetto
        self.crop_mesh_to_object(
            camera_distance_m=camera_distance_m,
            object_size_m=object_size_m,
            crop_margin_m=crop_margin_m
        )
        
        # Salva mesh
        mesh_file = self.save_mesh()
        
        # Opzionale: salva point cloud
        if save_point_cloud:
            pc_data, valid_mask = self.extract_point_cloud()
            if pc_data is not None:
                pc_file = self.save_point_cloud_ply(pc_data, valid_mask)
        
        print("\n" + "="*70)
        print("✅ RICOSTRUZIONE COMPLETATA!")
        print("="*70)
        if mesh_file:
            print(f"📄 Mesh: {mesh_file}")
        if save_point_cloud and pc_data is not None:
            print(f"☁️  Point cloud: {pc_file}")
        print("="*70)
    
    def cleanup(self):
        """Disabilita tracking e chiude camera"""
        self.zed.disable_spatial_mapping()
        self.zed.disable_positional_tracking()
        self.zed.close()
        print("\n🔒 Risorse rilasciate")


def main():
    """Esempio di utilizzo"""
    
    # Crea ricostruttore
    reconstructor = Object3DReconstructor(output_dir="ricostruzioni_3d")
    
    try:
        print("\n" + "="*70)
        print("CONFIGURAZIONE OGGETTO")
        print("="*70)
        
        # Chiedi parametri all'utente
        print("\n📏 Inserisci le informazioni sull'oggetto:")
        
        camera_dist = input("Distanza camera dall'oggetto (cm) [default: 35]: ").strip()
        camera_dist = float(camera_dist) / 100 if camera_dist else 0.35
        
        use_auto = input("Usare dimensioni automatiche? (s/n) [default: s]: ").strip().lower()
        
        if use_auto != 'n':
            object_size = None
            print("✅ Userò dimensioni automatiche")
        else:
            width = float(input("Larghezza oggetto (cm): ")) / 100
            height = float(input("Altezza oggetto (cm): ")) / 100
            depth = float(input("Profondità oggetto (cm): ")) / 100
            object_size = [width, height, depth]
            print(f"✅ Dimensioni impostate: {[f'{x*100:.1f}cm' for x in object_size]}")
        
        margin = input("Margine extra (cm) [default: 10]: ").strip()
        margin = float(margin) / 100 if margin else 0.10
        
        duration = input("Durata cattura (secondi) [default: 30]: ").strip()
        duration = int(duration) if duration else 30
        
        # Esegui ricostruzione
        reconstructor.full_reconstruction(
            camera_distance_m=camera_dist,
            object_size_m=object_size,
            crop_margin_m=margin,
            capture_duration=duration,
            save_point_cloud=True
        )
        
    except KeyboardInterrupt:
        print("\n⚠️  Interruzione da tastiera")
    
    except Exception as e:
        print(f"\n❌ Errore: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        reconstructor.cleanup()


if __name__ == "__main__":
    main()