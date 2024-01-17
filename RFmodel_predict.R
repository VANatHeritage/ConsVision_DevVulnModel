# RFmodel_predict
# Purpose: Run post-model processes for the development vulnerability random forest model.
# This includes functions for the following processes:
# - project: Create predictions raster
# - pred.adjust: Adjust predictions raster using protection multiplier, development, and water
# - indp.validate: Validate a model using validation points data set
# 
# Author: David Bucklin
# Created: 2021-10-21
# 
# Usage: The functions are called at the end of model.R, but they can be used independently in this script as well.
# Functions use input and output datasets with fixed paths/names; would need to adjust to run in a new environment.

setwd("D:/git/ConsVision_DevVulnModel")
library(sf)
library(randomForest)
library(raster)  # todo: update to terra
library(readxl)
library(SDMTools)
library(arcgisbinding)
library(ROCR)
library(ggplot2)
arc.check_product()
removeTmpFiles()


project <- function(proj.mod, year) {
  
  # Model name is the same as project output directory
  proj.o <- paste0("outputs/", proj.mod)
  print(proj.mod)
  
  # load model
  load(paste0(proj.o, "/", proj.mod, ".Rdata"))
  varnames <- row.names(as.data.frame(rf.final$importance))
  
  # load variables table
  file.vartable <- "inputs/vars/vars_DV.xlsx"
  vars <- read_excel(file.vartable)
  vars <- vars[vars$varname %in% varnames,]
  
  # make raster stack of included predictors
  ls <- list()
  for (i in 1:nrow(vars)) {
    # single-year variables should pull from the 2006 folder
    if (vars$static[i] == 1) fld <- "2006" else fld <- year
    ls[[vars$varname[i]]] <- paste0("inputs/vars/", fld , "/", vars$varname[i], ".tif")
  }
  r <- stack(ls)
  
  # output model raster base name
  out.mod <- paste0(proj.o, "/", proj.mod, "_", year)
  
  if (file.exists(paste0(out.mod, ".tif"))) {
    message("Prediction raster ", paste0(out.mod, ".tif"), " already exists, skipping...")
    next
  }
  message('Creating prediction raster for ', year, '...')
  beginCluster(7)
  r.pred <-  clusterR(r, predict, args = list(model=rf.final, type = "vote", index = 2), verbose = T)
  endCluster()
  writeRaster(r.pred, paste0(out.mod, ".tif"))
  
  return(r.pred)
}


pred.adjust <- function(proj.mod, year) {
  
  # Model name is the same as project output directory
  proj.o <- paste0("outputs/", proj.mod)
  print(proj.mod)
  out.mod <- paste0(proj.o, "/", proj.mod, "_", year)
  in.pred <- raster(paste0(out.mod, ".tif"))
  
  # masks
  dev.mask <- raster(paste0('inputs/masks/dev_mask_', year, '.tif'))
  wat.mask <- raster(paste0('inputs/masks/water_mask_', year, '.tif'))
  
  # protection multiplier
  if (year == "2019") conyear <- 'current' else conyear <- year
  pmult <- raster(paste0('inputs/masks/conslands_pmultBMI_', conyear, '.tif'))
  
  message('Applying protection multiplier...')
  r.pred2 <- round(in.pred * pmult)
  
  message('Setting BMI-1 lands to -1...')
  prot <- pmult
  prot[prot==0] <- NA
  r.pred2 <- raster::mask(r.pred2, prot, updatevalue=-1)
  
  message('Applying water mask...')
  r.pred2 <- mask(r.pred2, wat.mask)
  
  message('Setting already-developed areas to 101...')
  r.pred.mask <- raster::mask(r.pred2, dev.mask, updatevalue=101, filename = paste0(out.mod, "_final.tif"), overwrite = T, datatype = 'INT2S')
  return(r.pred.mask)
}

pred.upd <- function(proj.mod, in.year, upd.year, dev.rast, wat.rast, pmult) {
  
  # Model name is the same as project output directory
  proj.o <- paste0("outputs/", proj.mod)
  print(proj.mod)
  out.mod <- paste0(proj.o, "/", proj.mod, "_", in.year)
  in.pred <- raster(paste0(out.mod, ".tif"))
  out.rast <- paste0(out.mod, "_final_", upd.year, "upd.tif")
  message("Creating new raster: ", out.rast, "...")
  
  # masks
  dev.mask <- raster(dev.rast)
  wat.mask <- raster(wat.rast)
  # protection multiplier
  pmult <- raster(pmult)
  
  message('Applying protection multiplier...')
  r.pred2 <- round(in.pred * pmult)
  
  message('Setting BMI-1 lands to -1...')
  prot <- pmult
  prot[prot==0] <- NA
  r.pred2 <- raster::mask(r.pred2, prot, updatevalue=-1)
  
  message('Applying water mask...')
  r.pred2 <- raster::mask(r.pred2, wat.mask)
  
  message('Setting already-developed areas to 101...')
  r.pred.mask <- raster::mask(r.pred2, dev.mask, updatevalue=101, filename = out.rast, overwrite = T, datatype = 'INT2S')
  return(r.pred.mask)
}


indp.validate <- function(proj.mod) {
  
  message("Preparing validation points and prediction rasters...")
  # for output validation samples
  out.gdb <- 'outputs/samples_validation.gdb'
  
  # load model
  proj.o <- paste0("outputs/", proj.mod)
  load(paste0(proj.o, "/", proj.mod, ".Rdata"))
  varnames <- row.names(as.data.frame(rf.final$importance))
  
  # load variables table
  file.vartable <- "inputs/vars/vars_DV.xlsx"
  vars <- read_excel(file.vartable)
  vars <- vars[vars$varname %in% varnames,]
  
  # Validate model prediction with 2016->2019 change data.
  if (!exists("training.points")) training.points <- proj  # proj is the old name of object used
  validation.points <- gsub("TrainingPoints", "ValidationPoints", training.points)
  v1 <- arc.data2sf(arc.select(arc.open(paste0("inputs/samples/samples.gdb/", validation.points))))
  v1$y <- v1$DevStatus
  
  # protection multiplier
  pmult <- raster(paste0('inputs/masks/conslands_pmultBMI_2006.tif'))
  st_crs(v1) <- st_crs(pmult)
  
  # prediction rasters
  pred.rast.raw <- raster(paste0(proj.o, "/", proj.mod, "_2006.tif"))
  pred.rast.adj <- pred.rast.raw * pmult
  
  for (pt in c("Raw", "ProtAdj")) {
    if (pt == "Raw") pred.rast <- pred.rast.raw else pred.rast <- pred.rast.adj
    message(paste0('Validating ', pt, ' predictions...'))
    
    # Attach raster prediction values
    v1$pred <- extract(pred.rast, v1)
    
    # Get percentiles
    df.1 <- data.frame(class = 1, t(quantile(v1$pred[v1$y==1], c(0.01, 0.025, 0.05, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99))))
    df.0 <- data.frame(class = 0, t(quantile(v1$pred[v1$y==0], c(0.01, 0.025, 0.05, 0.1, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99))))
    df.quant <- rbind(df.1, df.0)
    write.csv(df.quant, paste0(proj.o, "/","indpValid", pt, "_quantiles.csv"), row.names = F)
    
    # Get final threshold from all point predictions
    opt.thresh <- optim.thresh(v1$y, v1$pred)
    thresh <- opt.thresh$`max.sensitivity+specificity`[1]
    
    # Validation AUCs
    p.rocr <- prediction(v1$pred, v1$y)
    aucpr <- performance(p.rocr, "aucpr")@y.values[[1]]
    print(paste0("AUC-PR: ", aucpr))
    aucroc <- performance(p.rocr, "auc")@y.values[[1]]
    print(paste0("AUC-PR: ", aucroc))
    
    # Color palette    
    palf <- colorRampPalette(c(rgb(38,115,0,1, maxColorValue = 255), rgb(245,245,122,1, maxColorValue = 255), rgb(230,76,0,1, maxColorValue = 255)))
    pal <- palf(256)
    
    # P-R curves
    if (pt == "ProtAdj") r.text <- "Protection-adjusted model value" else r.text <- "Model prediction value"
    perf <- performance(p.rocr, "prec", "rec")
    png(paste0(proj.o, "/", "indpValid", pt, "_prCurve.png"), width = 800, height = 720, pointsize = 18)
    par(mar = c(4, 4, 4, 6), cex.axis = 1.1, cex.lab=1.3, cex.main = 1.5)
    plot(perf, colorize=TRUE, colorize.palette=pal, ylim=c(0,1), downsampling = 0.2,
         main = paste0('Precision-Recall curve; AUC(PRC) = ', round(aucpr, 3)))
    baseline <- sum(v1$y==1) / nrow(v1)
    lines(x=c(0, 1), y = c(baseline, baseline), lty="dashed")
    mtext(r.text, side=4, padj=4, cex = 1.3)
    plot(perf, colorize=TRUE, colorize.palette=pal, add = T, lwd = 5)
    dev.off()
    
    if (pt == "Raw") {
      p1 <- data.frame(Model = proj.mod, validation='independent validation', 
                       Prediction_value =perf@alpha.values[[1]], Recall= perf@x.values[[1]], Precision=perf@y.values[[1]])
    }
    
    # ROC curves
    perf <- performance(p.rocr, "tpr", "fpr")
    png(paste0(proj.o, "/", "indpValid", pt, "_rocCurve.png"), width = 800, height = 720, pointsize = 18)
    par(mar = c(4, 4, 4, 6), cex.axis = 1.1, cex.lab=1.3, cex.main = 1.5)
    plot(perf, colorize=T, colorize.palette=pal, ylim = c(0, 1), main = paste0('ROC curve; AUC(ROC) = ', round(aucroc, 3)))
    lines(x=c(0, 1), y = c(0, 1), lty="dashed")
    mtext(r.text, side=4, padj=4, cex = 1.3)
    plot(perf, colorize=T, colorize.palette=pal, add = T, lwd = 5)
    dev.off()
    
    if (pt == "Raw") {
      a1 <- data.frame(Model = proj.mod, validation='independent validation',
                       Prediction_value =perf@alpha.values[[1]], FPR= perf@x.values[[1]], TPR=perf@y.values[[1]])
    }
    
    # write final stats CSV
    cols.keep <- c("foldid", "nsamp", "class0", "class1", "oob.error", "roc_auc", "prc_auc")
    res <- confusion.matrix(v1$y, v1$pred, thresh)
    df.ov <- data.frame(model = proj.mod, type = "independent validation 06-16",
                        roc_auc = aucroc, prc_auc = aucpr, nsamp = nrow(v1), class0 = sum(v1$y==0), class1 = sum(v1$y==1),
                        thresh = thresh, propCorrect = prop.correct(res), sens = sensitivity(res), spec = specificity(res), kappa = Kappa(res))
    write.csv(df.ov[,1:7], file=paste0(proj.o, "/indpValid", pt, "_stats.csv"), row.names = F)
    
    # Output CV points to GDB
    arc.write(paste0(out.gdb, "/", proj.mod, "_indpValid", pt, "_pts"), v1, overwrite=T)
  }
  
  # combined P-R curve (with CV)
  p.rocr <- prediction(df.cv.full$pred, df.cv.full$y)
  perf <- performance(p.rocr, "prec", "rec")
  p2 <- rbind(p1, 
              data.frame(Model = proj.mod, validation='cross-validation', 
                         Prediction_value =perf@alpha.values[[1]], Recall= perf@x.values[[1]], Precision=perf@y.values[[1]]))
  g <- ggplot(p2) + geom_line(aes(x=Recall, y=Precision, col=validation), size=0.8, alpha=0.7) + 
    scale_color_discrete() + ggtitle(paste0("Precision-Recall curves: ", proj.mod, " (raw)"))
  ggsave(paste0(proj.o, "/prCurve_validationCompare.png"), g, units="in", width = 11, height= 8)
  # ROC
  perf <- performance(p.rocr, "tpr", "fpr")
  a2 <- rbind(a1, data.frame(Model = proj.mod, validation='cross-validation',
                             Prediction_value =perf@alpha.values[[1]], FPR= perf@x.values[[1]], TPR=perf@y.values[[1]]))
  g <- ggplot(a2) + geom_line(aes(x=FPR, y=TPR, col=validation), size=0.8, alpha=0.7) + 
    scale_color_discrete() + ggtitle(paste0("ROC curves: ", proj.mod, " (raw)"))
  ggsave(paste0(proj.o, "/rocCurve_validationCompare.png"), g, units="in", width = 11, height= 8)
  
  return(TRUE)
}

# Example workflow

# proj.mod <- "DevVuln_AllVars_20220510"
# year <- '2006'
# raw <- project(proj.mod, year)
# adj <- pred.adjust(proj.mod, year)
# indp.validate(proj.mod)

# to make an updated version of existing model (mask and protection multiplier updates)
# proj.mod <- "DevVuln_AllVars_20220510"
# in.year <- "2019"
# upd.year <- "2023"
# dev.rast <- "inputs/masks/dev_mask_2021.tif"
# wat.rast <- "inputs/masks/water_mask_2021.tif"
# pmult <- "inputs/masks/conslands_pmultBMI_2023.tif"
# pred.upd(proj.mod, in.year, upd.year, dev.rast, wat.rast, pmult) 


# end
